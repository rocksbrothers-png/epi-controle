'use strict';

// Public capability endpoints. No session or tenant is inferred on the client.
(function () {
  const endpoint = token => '/api/portal/supplier/' + encodeURIComponent(token);
  const headers = locale => ({'Accept-Language':locale});
  function data(token, locale) {
    return fetch(endpoint(token), {headers:headers(locale)});
  }
  function post(token, action, body, locale) {
    return fetch(endpoint(token) + '/' + action, {
      method:'POST', headers:{'Content-Type':'application/json', ...headers(locale)},
      body:JSON.stringify(body)
    });
  }
  globalThis.__EPI_SUPPLIER_PORTAL_API__ = Object.freeze({
    data,
    answer:(token,body,locale) => post(token,'quote',body,locale),
    confirm:(token,body,locale) => post(token,'confirm',body,locale)
  });
})();
