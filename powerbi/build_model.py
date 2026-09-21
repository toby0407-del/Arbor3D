"""Generate a reviewable Tabular model, M queries and Fabric type contract locally."""
import json
from pathlib import Path
from analytics.core import FIELDS, VERSION

BOOL = {'strict_13m','manual_strict_13m','review_required','negative_change'}
NUM = {'auto_dbh_cm','manual_dbh_cm','manual_height_m','error_cm','absolute_error_cm','squared_error_cm2','ape_pct','yolo_confidence','arc_coverage_deg','days','delta_dbh_cm','annualized_delta_cm','dbh_input_cm','height_m','coefficient','carbon_d','co2_equivalent_ton'}
DATES = {'observed_at','manual_measured_at','from_date','to_date'}
MEASURES = {
    'Observations': 'COUNTROWS(FactObservation)',
    'Observed Trees': 'DISTINCTCOUNT(FactObservation[tree_key])',
    'Valid Pairs': 'COALESCE(CALCULATE(COUNTROWS(FactObservation), FactObservation[comparison_status] = "paired"), 0)',
    'MAE cm': 'AVERAGE(FactObservation[absolute_error_cm])',
    'RMSE cm': 'VAR M = AVERAGE(FactObservation[squared_error_cm2]) RETURN IF(ISBLANK(M), BLANK(), SQRT(M))',
    'Bias cm': 'AVERAGE(FactObservation[error_cm])',
    'MAPE percent': 'AVERAGE(FactObservation[ape_pct])',
    'Review Observations': 'COALESCE(CALCULATE(COUNTROWS(FactObservation), FactObservation[review_required] = TRUE()), 0)',
    'Review Rate': 'DIVIDE([Review Observations], [Observations])',
    'Estimated CO2 Snapshot ton': 'IF(HASONEVALUE(DimScan[scan_key]), SUM(FactEstimate[co2_equivalent_ton]), BLANK())',
    'Mean Observed Delta cm': 'IF(HASONEVALUE(FactGrowth[source]) && HASONEVALUE(FactGrowth[method]), AVERAGE(FactGrowth[delta_dbh_cm]), BLANK())',
}
# Production accuracy measures always exclude synthetic demonstrations.
for _name in ('Valid Pairs', 'MAE cm', 'RMSE cm', 'Bias cm', 'MAPE percent'):
    MEASURES[_name] = 'CALCULATE((' + MEASURES[_name] + '), KEEPFILTERS(FactObservation[dataset_kind] = "observed"))'
MEASURES.update({
    'Demo Pairs': 'CALCULATE(COUNTROWS(FactObservation), FactObservation[dataset_kind] = "simulated", FactObservation[comparison_status] = "paired")',
    'Demo MAE cm': 'CALCULATE(AVERAGE(FactObservation[absolute_error_cm]), FactObservation[dataset_kind] = "simulated")',
    'Growth Records': 'COALESCE(COUNTROWS(FactGrowth), 0)',
    'Average DBH cm': 'AVERAGE(FactObservation[auto_dbh_cm])',
})

def main():
    root=Path(__file__).parent
    schema={}; tables=[]; queries=[]
    for name, fields in FIELDS.items():
        if name=='Summary': continue
        schema[name]={f:'boolean' if f in BOOL else 'double' if f in NUM else 'date' if f in DATES else 'string' for f in fields}
        pairs=', '.join('{"'+f+'", '+('type logical' if f in BOOL else 'type number' if f in NUM else 'type date' if f in DATES else 'type text')+'}' for f in fields)
        m='let\n  Raw = Csv.Document(File.Contents(AnalyticsFolder & "/'+name+'.csv"), [Delimiter=",", Columns='+str(len(fields))+', Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n  Headers = Table.PromoteHeaders(Raw, [PromoteAllScalars=true]),\n  Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),\n  Typed = Table.TransformColumnTypes(Nulls, {'+pairs+'}, "en-US")\nin Typed'
        queries.append('// Query: '+name+'\n'+m+'\n')
        table={'name':name,'columns':[{'name':f,'dataType':'boolean' if f in BOOL else 'double' if f in NUM else 'dateTime' if f in DATES else 'string','sourceColumn':f,'summarizeBy':'none'} for f in fields], 'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':m.splitlines()}}]}
        if name=='FactObservation':
            table['measures']=[{'name':k,'expression':v,'description':'Offline draft; respects report filter context. Valid pairs require same-day strict-height manual measurements.','formatString':'0.00%;-0.00%;0.00%' if k=='Review Rate' else '0.000'} for k,v in MEASURES.items()]
        tables.append(table)
    relationships=[]
    for fact in ('FactObservation','FactEstimate','FactGrowth'):
        for dim,col,source in [('DimTree','tree_key','tree_key'),('DimScan','scan_key','to_scan_key' if fact=='FactGrowth' else 'scan_key')]:
            relationships.append({'name':fact+'_'+dim,'fromTable':fact,'fromColumn':source,'toTable':dim,'toColumn':col,'crossFilteringBehavior':'oneDirection','fromCardinality':'many','toCardinality':'one'})
    model={'name':'Arbor3DAnalytics','compatibilityLevel':1600,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','expressions':[{'name':'AnalyticsFolder','kind':'m','expression':'"REPLACE_WITH_ABSOLUTE_OUTPUT_FOLDER" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'}],'tables':tables,'relationships':relationships}}
    (root/'model.bim').write_text(json.dumps(model,ensure_ascii=False,indent=2), encoding='utf-8')
    (root/'queries.pq').write_text('// Create a Text parameter named AnalyticsFolder, then create each named query separately.\n\n'+'\n'.join(queries), encoding='utf-8')
    (root/'measures.dax').write_text('\n\n'.join(k+' =\n'+v for k,v in MEASURES.items()), encoding='utf-8')
    (root.parent/'fabric/table-schema.json').write_text(json.dumps(schema,indent=2), encoding='utf-8')
    # A machine-readable, exact JSON data contract used by downstream validation.
    definitions={}
    for table, fields in schema.items():
        props={}
        for field,kind in fields.items():
            t='boolean' if kind=='boolean' else 'number' if kind=='double' else 'string'
            props[field]={'type':[t,'null']}
        definitions[table]={'type':'array','items':{'type':'object','additionalProperties':False,'required':list(props),'properties':props}}
    definitions['Summary']={'type':'array','items':{'type':'object','required':FIELDS['Summary']}}
    contract={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'Arbor3D Analytics v1.1','type':'object','required':['schema_version','tables'],'additionalProperties':False,'properties':{'schema_version':{'const':VERSION},'tables':{'type':'object','required':list(FIELDS),'additionalProperties':False,'properties':definitions}}}
    (root.parent/'analytics/schema.json').write_text(json.dumps(contract,indent=2), encoding='utf-8')

if __name__=='__main__': main()
