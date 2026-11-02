"""Canonical month/day checkbox mapping for NC Form 22 08/2026."""
from __future__ import annotations
from calendar import monthrange
from datetime import date
from pypdf import PdfReader

MONTH_SUFFIX = {1:'0',2:'1.0',3:'1.1',4:'1.2',5:'1.3',6:'1.4',7:'1.5',8:'1.6',9:'1.7',10:'2',11:'3',12:'4'}

def _prefix(day:int)->str:
    # PDF omitted Check Box2; visual day 2 maps to Check Box3, etc.
    return f'Check Box{day if day==1 else day+1}'

def field_for_date(value: date)->str:
    return f'{_prefix(value.day)}.{MONTH_SUFFIX[value.month]}'

def build_day_grid_map(template:str, year:int)->dict[str,str]:
    fields=PdfReader(template).get_fields() or {}
    result={}
    for month in range(1,13):
        for day in range(1,monthrange(year,month)[1]+1):
            d=date(year,month,day)
            name=field_for_date(d)
            if name not in fields:
                raise KeyError(f'Missing expected field {name} for {d.isoformat()}')
            result[d.isoformat()]=name
    return result
