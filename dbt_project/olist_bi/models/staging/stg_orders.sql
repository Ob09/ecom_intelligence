-- stg_orders.sql
-- Cleans the raw orders table
-- Renames columns to readable names
-- Converts date strings to proper timestamps

with source as (

    -- Pull everything from the raw orders table
    -- 'source' is just an alias we give to the raw table
    select * from {{ source('olist', 'raw_orders') }}

),

renamed as (

    select
        -- Rename order_id to a cleaner name
        order_id,

        -- Rename customer_id
        customer_id,

        -- Rename order_status
        order_status,

        -- Convert date strings to proper timestamps
        -- ::timestamp is PostgreSQL syntax for casting text to timestamp
        order_purchase_timestamp::timestamp      as purchased_at,
        order_approved_at::timestamp             as approved_at,
        order_delivered_carrier_date::timestamp  as shipped_at,
        order_delivered_customer_date::timestamp as delivered_at,
        order_estimated_delivery_date::timestamp as estimated_delivery_at

    from source

)

select * from renamed