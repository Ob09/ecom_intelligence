with source as (

    select * from {{ source('olist', 'raw_sellers') }}

),

renamed as (

    select
        seller_id,
        seller_zip_code_prefix  as zip_code,
        seller_city             as city,
        seller_state            as state

    from source

)

select * from renamed