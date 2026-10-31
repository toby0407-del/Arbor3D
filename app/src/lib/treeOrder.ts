export function compareTreeIds(a: {Tree_ID:string}, b: {Tree_ID:string}): number {
  return a.Tree_ID.localeCompare(b.Tree_ID, "en", {numeric:true, sensitivity:"base"});
}
