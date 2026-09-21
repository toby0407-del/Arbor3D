"""Copy into a Fabric Spark notebook ONLY after future cloud-cost authorization.
The local default is a no-network preview. Upload a complete analytics snapshot and
schema file to Files/arbor3d/gold/<batch_id>/ before execution. Re-running replaces
these dedicated arbor_* tables with that complete snapshot; never append duplicates.
"""
import json

def load(spark, snapshot_root, schema, *, authorized=False):
    if not authorized:
        return {'mode':'preview','root':snapshot_root,'tables':['arbor_'+name for name in schema], 'cloud_write':False}
    from pyspark.sql.types import StructType, StructField, StringType, DoubleType, BooleanType, DateType
    types={'string':StringType,'double':DoubleType,'boolean':BooleanType,'date':DateType}
    staged=[]
    for name, fields in schema.items():
        if not name.replace('_','').isalnum(): raise ValueError('Invalid table name')
        explicit=StructType([StructField(k,types[v](),True) for k,v in fields.items()])
        frame=(spark.read.schema(explicit).option('header',True).option('encoding','UTF-8').option('mode','FAILFAST').option('multiLine',True).option('escape','"').csv(snapshot_root+'/'+name+'.csv'))
        frame.cache(); frame.count()  # Validate every frame before beginning writes.
        staged.append((name,frame))
    for name,frame in staged:
        frame.write.format('delta').mode('overwrite').option('overwriteSchema','true').saveAsTable('arbor_'+name)
        frame.unpersist()
    return {'cloud_write':True,'tables':[name for name,_ in staged]}

if __name__=='__main__':
    from pathlib import Path
    print(json.dumps(load(None,'Files/arbor3d/gold/REPLACE_BATCH',json.loads(Path('fabric/table-schema.json').read_text())),indent=2))
