'use strict';
// A conservative candidate selector, not an authorization or production Shopify adapter.
function matchOrder(orders, {storeId, email, orderNumber}) {
  const norm = value => typeof value === 'string' ? value.trim().toLowerCase() : '';
  if (!norm(storeId) || !norm(email)) return {status: 'insufficient-input', ids: []};
  const candidates = orders.filter(o => o.storeId === storeId && norm(o.email) === norm(email));
  const selected = orderNumber === undefined ? candidates : candidates.filter(o => o.orderNumber === orderNumber);
  return {status: selected.length === 1 ? 'candidate' : selected.length ? 'ambiguous' : 'no-match', ids: selected.map(o => o.id)};
}
module.exports = {matchOrder};
