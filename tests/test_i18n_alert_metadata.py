"""Presentation metadata must preserve operational alert selection and authority."""
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from modules.alerts.service import compute_alerts


@pytest.mark.parametrize('stock,status,title,suffix',[
    (-2,'critical','Saldo negativo','negative'),
    (0,'critical','Estoque zerado','zero'),
    (4,'critical','Estoque abaixo do mínimo','belowMinimum'),
    (10,'critical','Estoque no limite mínimo','atMinimum'),
    (11,'near_minimum','Estoque próximo do mínimo','nearMinimum'),
])
def test_stock_metadata_is_additive_and_keeps_identifiers_and_legacy_text(stock,status,title,suffix):
    item={'stock':stock,'minimum_stock':10,'stock_status':status,'epi_name':'Luva original',
          'company_name':'Empresa original','unit_name':'Unidade original','unit_measure':'par',
          'company_id':41,'unit_id':42,'epi_id':43,
          'size_balances':[{'glove_size':'G','size':'N/A','uniform_size':'N/A','quantity':stock}]}
    original={**item,'size_balances':[dict(item['size_balances'][0])]}
    with patch('modules.alerts.service.physical_summary_map',return_value={}):
        alerts=compute_alerts(None,{'role':'admin'},fetch_low_stock_items=lambda *_:[item],
            actor_operational_unit_id=lambda *_:42,fetch_epis=lambda *_:[])
    assert len(alerts)==1
    alert=alerts[0]
    assert alert['title']==f'{title}: Luva original'
    assert alert['description']==f'Empresa original / Unidade original - saldo atual de {stock} par(s), mínimo 10. | Tamanhos em estoque: Luva:G×{stock}'
    assert (alert['company_id'],alert['unit_id'],alert['epi_id'])==(41,42,43)
    assert alert['presentation']['title_key']=='operationalAlerts.stock.'+suffix
    assert alert['presentation']['params']['stock']==stock
    assert alert['presentation']['params']['measure']=='par'
    assert item==original


@pytest.mark.parametrize('days,description', [(-1,'expiredDescription'),(3,'expiringDescription')])
def test_physical_dates_counts_and_scope_are_not_replaced_by_catalogue(days,description):
    today=date.today();physical_date=(today+timedelta(days=days)).isoformat()
    epi={'id':43,'company_id':41,'unit_id':42,'active':1,'name':'Luva original','company_name':'Empresa original',
         'stock':3,'unit_measure':'par','ca_expiry':(today+timedelta(days=10)).isoformat(),
         'epi_validity_date':'2099-01-01'}
    physical={43:{'as_of_date':today.isoformat(),'nearest_known_expiry':physical_date,
                  'warning_days':30,'unknown':2,'expiring':4}}
    with patch('modules.alerts.service.physical_summary_map',return_value=physical):
        alerts=compute_alerts(None,{'role':'admin'},fetch_low_stock_items=lambda *_:[],
            actor_operational_unit_id=lambda *_:42,fetch_epis=lambda *_:[epi])
    manufacturer=next(a for a in alerts if a['category']=='manufacturer')
    assert manufacturer['presentation']['description_key']=='operationalAlerts.manufacturer.'+description
    assert manufacturer['presentation']['params']['date']==physical_date
    assert manufacturer['presentation']['params']['days']==days
    unknown=next(a for a in alerts if a['category']=='physical_unknown')
    assert unknown['presentation']['params']=={'epi':'Luva original','count':2}
    assert unknown['description']=='Luva original: 2 peça(s) física(s).'
    assert unknown['unit_id']==42 and unknown['company_id']==41 and unknown['epi_id']==43
    assert any(a['category']=='physical_expiring' for a in alerts)==(days<0)


def test_missing_operational_scope_does_not_leak_alert_metadata():
    alerts=compute_alerts(None,{'role':'admin'},fetch_low_stock_items=lambda *_:pytest.fail('scope bypass'),
        actor_operational_unit_id=lambda *_:None,fetch_epis=lambda *_:pytest.fail('scope bypass'))
    assert alerts==[]
