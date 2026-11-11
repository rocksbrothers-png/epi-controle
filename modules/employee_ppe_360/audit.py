"""Ficha 360° de EPI — auditoria de abertura (DF-7).

ÚNICA escrita do pacote ``employee_ppe_360``. A guarda de somente-leitura em
``tests/test_employee_ppe_360_f0_contract.py`` permite exatamente este arquivo,
e só por meio dos registradores oficiais — nenhum SQL de escrita aqui.

Sem tabela nova: cada resultado vai para a trilha existente que o comporta.

* **Concedida** → ``ficha_epi_audit_log`` (``view_360``), a mesma trilha da
  Ficha de EPI: aparece no filtro de auditoria da Configuração, com ator,
  papel, empresa, unidade, colaborador e horário.
* **Negada** → ``company_audit_logs`` da empresa do ATOR
  (``ppe360_view_denied``), com o código do resultado e o id pedido. A trilha
  da Ficha não serve aqui: ela exige colaborador, unidade e empresa existentes
  (chaves estrangeiras), e uma negativa por "inexistente" ou "outra empresa"
  não tem — nem pode ter — esses vínculos. O nome do colaborador nunca é
  gravado numa negativa: seria revelar um registro que o ator não pode ver.
* **Sempre** → log estruturado da aplicação (``employee_ppe_360.view``), que
  é a única trilha possível para o Admin Master (sem empresa).

Nada do conteúdo da Ficha é registrado.
"""

from __future__ import annotations

from epi_backend.http_utils import structured_log

ACTION_GRANTED = 'view_360'
ACTION_DENIED = 'ppe360_view_denied'
LOG_EVENT = 'employee_ppe_360.view'


def _ip(handler) -> str:
    return str(getattr(handler, 'client_address', ('',))[0] or '')


def _user_agent(handler) -> str:
    headers = getattr(handler, 'headers', None)
    return str(headers.get('User-Agent', '') if headers is not None else '')[:300]


def record_granted(connection, handler, actor, employee, *, unit_id):
    from modules.ficha.service import register_ficha_epi_audit

    register_ficha_epi_audit(
        connection,
        actor=actor,
        employee={'id': employee['id'], 'name': employee.get('name') or '',
                  'unit_id': unit_id or employee.get('unit_id') or 0, 'company_id': employee['company_id']},
        action=ACTION_GRANTED,
        ip_address=_ip(handler),
        user_agent=_user_agent(handler),
    )
    connection.commit()
    structured_log('info', LOG_EVENT, result='granted', actor_user_id=actor.get('id'),
                   actor_role=actor.get('role'), company_id=employee.get('company_id'),
                   employee_id=employee.get('id'), unit_id=unit_id)


def record_denied(connection, handler, actor, *, requested_employee_id, code):
    from core.audit import register_company_audit

    company_id = actor.get('company_id')
    if company_id:
        register_company_audit(
            connection, int(company_id), actor, ACTION_DENIED,
            f'Abertura da Ficha 360° negada ({code}).',
            [{'requested_employee_id': int(requested_employee_id or 0), 'result': code,
              'actor_role': actor.get('role') or '', 'ip_address': _ip(handler)}],
        )
        connection.commit()
    structured_log('warning', LOG_EVENT, result='denied', code=code, actor_user_id=actor.get('id'),
                   actor_role=actor.get('role'), company_id=company_id,
                   requested_employee_id=int(requested_employee_id or 0))


__all__ = ['ACTION_DENIED', 'ACTION_GRANTED', 'LOG_EVENT', 'record_denied', 'record_granted']


def record_in_use(connection, actor, requested_employee_id, *, code, page=None, scope=None, count=0):
    """F2 section audit: metadata only, never cursor, row contents or target name."""
    from core.audit import register_company_audit

    granted = code == 'OK'
    details = {'requested_employee_id': requested_employee_id, 'code': code}
    if actor:
        details['actor_role'] = actor['role']
    if page:
        details.update(limit=page['limit'], has_cursor=page['cursor'] is not None)
    if scope:
        details.update(mode=scope['mode'], authorized_unit_ids=scope['authorized_unit_ids'])
    if granted:
        details['returned_count'] = count
    if actor and actor.get('company_id'):
        register_company_audit(connection, int(actor['company_id']), actor,
                               'ppe360_in_use_view' if granted else 'ppe360_in_use_denied',
                               'Consulta de EPIs em uso.', [details])
        connection.commit()
    structured_log('info' if granted else 'warning', 'employee_ppe_360.in_use',
                   result='granted' if granted else 'denied',
                   actor_user_id=actor.get('id') if actor else None,
                   company_id=actor.get('company_id') if actor else None, **details)
