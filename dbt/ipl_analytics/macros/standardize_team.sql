{% macro standardize_team(team_expression) -%}
    case upper(trim({{ team_expression }}))
        when 'ROYAL CHALLENGERS BANGALORE' then 'Royal Challengers Bengaluru'
        when 'DELHI DAREDEVILS' then 'Delhi Capitals'
        when 'KINGS XI PUNJAB' then 'Punjab Kings'
        else initcap(trim({{ team_expression }}))
    end
{%- endmacro %}
