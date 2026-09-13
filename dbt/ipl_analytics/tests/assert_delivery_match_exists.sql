-- Every delivery must belong to an existing match.
select deliveries.delivery_id, deliveries.match_id
from {{ ref('stg_deliveries') }} deliveries
left join {{ ref('dim_match') }} matches using (match_id)
where matches.match_key is null
