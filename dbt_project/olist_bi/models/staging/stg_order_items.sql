with source as (

    select * from {{ source('olist', 'raw_order_items') }}

),

renamed as (

    select
        order_id,
        order_item_id             as item_sequence,
        product_id,
        seller_id,
        shipping_limit_date::timestamp as shipping_limit_at,
        price,
        freight_value             as freight_cost

    from source

)

select * from renamed