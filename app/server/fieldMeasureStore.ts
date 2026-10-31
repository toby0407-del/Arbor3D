import { promises as fs } from "node:fs";
import path from "node:path";
import { CosmosClient, type Container } from "@azure/cosmos";
import { AzureCliCredential, DefaultAzureCredential, ManagedIdentityCredential } from "@azure/identity";
import { applyMeasurePatch, type MeasurePatch } from "./fieldMeasurePatch.js";

export type FieldMeasureRecord = Record<string, {
  strict13m?: boolean;
  dbhCm: string;
  note: string;
  heightM: string;
  coeff: string;
  measuredAt: string;
}>;

export type MeasureAudit = { updatedAt: string; updatedBy: string };

export interface FieldMeasureStore {
  readonly provider: "cosmos" | "file";
  read(scanId: string): Promise<FieldMeasureRecord>;
  write(scanId: string, measures: FieldMeasureRecord, audit: MeasureAudit): Promise<void>;
  check(): Promise<void>;
  patch(scanId: string, treeId: string, patch: MeasurePatch, audit: MeasureAudit): Promise<FieldMeasureRecord>;
}

type CosmosDocument = {
  id: string;
  type: "field-measures";
  schemaVersion: 1;
  scanId: string;
  measures: FieldMeasureRecord;
  updatedAt: string;
  updatedBy: string;
};

const containers = new Map<string, Promise<Container>>();

async function cosmosContainer(env: Record<string, string | undefined>) {
  const endpoint = env.AZURE_COSMOS_ENDPOINT?.trim();
  if (!endpoint || !/^https:\/\//i.test(endpoint)) {
    throw new Error("AZURE_COSMOS_ENDPOINT 必須是 HTTPS Cosmos DB for NoSQL endpoint");
  }
  const databaseId = env.AZURE_COSMOS_DATABASE?.trim() || "Arbor3D";
  const containerId = env.AZURE_COSMOS_CONTAINER?.trim() || "FieldMeasures";
  const key = `${endpoint}|${databaseId}|${containerId}`;
  let pending = containers.get(key);
  if (!pending) {
    pending = (async () => {
      const managedClientId = env.AZURE_CLIENT_ID?.trim();
      const credential = env.WEBSITE_HOSTNAME
        ? managedClientId
          ? new ManagedIdentityCredential({ clientId: managedClientId })
          : new ManagedIdentityCredential()
        : env.ARBOR_AZURE_AUTH === "cli" ? new AzureCliCredential() : new DefaultAzureCredential();
      const client = new CosmosClient({ endpoint, aadCredentials: credential });
      if (env.ARBOR_COSMOS_AUTO_CREATE === "YES_I_ACCEPT_AZURE_CHANGES") {
        const { database } = await client.databases.createIfNotExists({ id: databaseId });
        const { container } = await database.containers.createIfNotExists({
          id: containerId,
          partitionKey: { paths: ["/scanId"] },
          indexingPolicy: {
            automatic: true,
            indexingMode: "consistent",
            includedPaths: [
              { path: "/scanId/?" },
              { path: "/type/?" },
              { path: "/updatedAt/?" },
            ],
            excludedPaths: [{ path: "/*" }],
          },
        });
        return container;
      }
      return client.database(databaseId).container(containerId);
    })();
    containers.set(key, pending);
    void pending.catch(()=>containers.delete(key));
  }
  return pending;
}

class CosmosFieldMeasureStore implements FieldMeasureStore {
  readonly provider = "cosmos" as const;
  private readonly env: Record<string, string | undefined>;

  constructor(env: Record<string, string | undefined>) {
    this.env = env;
  }

  async check() {
    const container = await cosmosContainer(this.env);
    await container.read();
  }

  async read(scanId: string) {
    const container = await cosmosContainer(this.env);
    try {
      const { resource } = await container.item(`field-measures:${scanId}`, scanId).read<CosmosDocument>();
      return resource?.measures ?? {};
    } catch (error) {
      if ((error as { code?: number }).code === 404) return {};
      throw error;
    }
  }

  async write(scanId: string, measures: FieldMeasureRecord, audit: MeasureAudit) {
    const container = await cosmosContainer(this.env);
    const document: CosmosDocument = {
      id: `field-measures:${scanId}`,
      type: "field-measures",
      schemaVersion: 1,
      scanId,
      measures,
      ...audit,
    };
    await container.items.upsert(document);
  }

  async patch(scanId: string, treeId: string, patch: MeasurePatch, audit: MeasureAudit) {
    const container = await cosmosContainer(this.env);
    const item = container.item(`field-measures:${scanId}`, scanId);
    for (let attempt = 0; attempt < 5; attempt += 1) {
      let current: (CosmosDocument & { _etag?: string }) | undefined;
      try { current = (await item.read<CosmosDocument & { _etag?: string }>()).resource; }
      catch (error) { if ((error as { code?: number }).code !== 404) throw error; }
      const document: CosmosDocument = { id: `field-measures:${scanId}`, type: "field-measures", schemaVersion: 1,
        scanId, measures: applyMeasurePatch(current?.measures ?? {}, treeId, patch), ...audit };
      try {
        if (current) {
          if (!current._etag) throw new Error("資料庫未回傳版本資訊，無法安全更新");
          await item.replace(document, { accessCondition: { type: "IfMatch", condition: current._etag } });
        } else { await container.items.create(document); }
        return document.measures;
      } catch (error) {
        if (![409, 412].includes(Number((error as { code?: number }).code))) throw error;
      }
    }
    throw new Error("其他使用者正在更新此盤點，請稍後重試");
  }
}

class FileFieldMeasureStore implements FieldMeasureStore {
  readonly provider = "file" as const;
  private readonly filename: string;
  private writeQueue = Promise.resolve();

  constructor(root: string) {
    this.filename = path.resolve(root, ".runtime", "field-measures.json");
  }

  private async all() {
    try {
      return JSON.parse(await fs.readFile(this.filename, "utf8")) as Record<string, {
        measures?: FieldMeasureRecord;
      }>;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") return {};
      throw error;
    }
  }

  async read(scanId: string) {
    return (await this.all())[scanId]?.measures ?? {};
  }

  async check() { await this.all(); }

  async write(scanId: string, measures: FieldMeasureRecord, audit: MeasureAudit) {
    const operation = this.writeQueue.then(async () => {
      const store = await this.all();
      store[scanId] = { measures, ...audit };
      await fs.mkdir(path.dirname(this.filename), { recursive: true });
      const temporary = `${this.filename}.${process.pid}.tmp`;
      await fs.writeFile(temporary, `${JSON.stringify(store, null, 2)}\n`, { mode: 0o600 });
      await fs.rename(temporary, this.filename);
    });
    this.writeQueue = operation.catch(() => undefined);
    await operation;
  }

  async patch(scanId: string, treeId: string, patch: MeasurePatch, audit: MeasureAudit) {
    const operation = this.writeQueue.then(async () => {
      const store = await this.all();
      const measures = applyMeasurePatch(store[scanId]?.measures ?? {}, treeId, patch);
      store[scanId] = { measures, ...audit };
      await fs.mkdir(path.dirname(this.filename), { recursive: true });
      const temporary = `${this.filename}.${process.pid}.tmp`;
      await fs.writeFile(temporary, `${JSON.stringify(store, null, 2)}\n`, { mode: 0o600 });
      await fs.rename(temporary, this.filename);
      return measures;
    });
    this.writeQueue = operation.then(() => undefined, () => undefined);
    return operation;
  }
}

export function createFieldMeasureStore(
  root: string,
  env: Record<string, string | undefined>,
): FieldMeasureStore {
  return env.AZURE_COSMOS_ENDPOINT?.trim()
    ? new CosmosFieldMeasureStore(env)
    : new FileFieldMeasureStore(root);
}
