with source as (

    select * from {{ source('olist', 'raw_payments') }}

),

renamed as (

    select
        order_id,
        payment_sequential        as payment_sequence,
        payment_type,
        payment_installments      as installments,
        payment_value             as payment_amount

    from source

)

select * from renamed