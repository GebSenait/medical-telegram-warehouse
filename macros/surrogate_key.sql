{% macro surrogate_key(field_list) -%}
  {#
    Generate a surrogate key from a list of fields.
    Uses MD5 hash for consistent key generation.
  #}
  md5(
    {%- for field in field_list -%}
      coalesce(cast({{ field }} as varchar), '')
      {%- if not loop.last %} || '|' || {% endif -%}
    {%- endfor -%}
  )
{%- endmacro %}
