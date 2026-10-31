"""Presentation negotiation remains after the existing authorization/scope ports."""
import importlib
import io
import re
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

from modules.i18n.presentation import request_locale


@pytest.mark.parametrize('module_name,handler_name,scope_name,sender_name,resource_name',[
    ('quotes_routes','handle_post_quote_send','_load_scoped_quote','send_quote_to_supplier',None),
    ('quotes_routes','handle_post_purchase_order_send','ensure_purchase_order_action_scope','send_po_to_supplier','get_purchase_order_by_id'),
    ('supplier_portal_routes','handle_post_quote_portal_link','ensure_quote_scope','send_portal_link_email','get_quote_by_id'),
    ('supplier_portal_routes','handle_post_po_portal_link','ensure_purchase_order_action_scope','send_portal_link_email','get_purchase_order_by_id'),
])
@pytest.mark.parametrize('outcome',['allowed','auth_denied','scope_denied'])
def test_locale_is_presentation_only_after_existing_guards(monkeypatch,module_name,handler_name,scope_name,sender_name,resource_name,outcome):
    routes=importlib.import_module('modules.purchases.'+module_name)
    events=[];sent=[]
    actor={'id':23,'company_id':41,'operational_unit_id':42,'role':'buyer'}
    record={'id':7,'company_id':41,'unit_id':42}
    class Connection:
        def close(self):events.append('close')
        def commit(self):events.append('commit')
    connection=Connection()
    handler=SimpleNamespace(path='/api/document',command='POST',headers={'Accept-Language':'fr-FR'},client_address=('127.0.0.1',1234),wfile=io.BytesIO())
    handler.send_response=lambda *_:None
    handler.send_header=lambda *_:None
    handler.end_headers=lambda:None
    monkeypatch.setattr(routes,'get_connection',lambda:connection)
    monkeypatch.setattr(routes,'resolve_actor_user_id',lambda *_:23)
    def authorize(*args,**kwargs):
        events.append('authorize')
        if outcome=='auth_denied':raise PermissionError('denied')
        return actor
    def scope(*args,**kwargs):
        events.append('scope')
        assert args[0] is connection and args[1] is actor
        if outcome=='scope_denied':raise PermissionError('crossed scope')
        return record
    def language(*args):
        events.append('locale')
        return request_locale(*args)
    def sender(*args,**kwargs):
        events.append('sender')
        assert args[0] is connection and args[1] is actor
        sent.append((args,kwargs))
        return record
    monkeypatch.setattr(routes,'authorize_action',authorize)
    monkeypatch.setattr(routes,scope_name,scope)
    monkeypatch.setattr(routes,'request_locale',language)
    monkeypatch.setattr(routes,sender_name,sender)
    if resource_name:monkeypatch.setattr(routes,resource_name,lambda *_:record)
    call=lambda:getattr(routes,handler_name)(handler,urlparse('/api/document?lang=fr-FR'),{'actor_user_id':23},re.match(r'(\d+)','7'))
    if outcome=='allowed':
        call()
        assert events==['authorize','scope','locale','sender','commit','close']
        assert sent[0][1]['locale']=='fr-FR'
        assert actor=={'id':23,'company_id':41,'operational_unit_id':42,'role':'buyer'}
    else:
        with pytest.raises(PermissionError):call()
        assert 'locale' not in events and 'sender' not in events and 'commit' not in events
        assert not sent
