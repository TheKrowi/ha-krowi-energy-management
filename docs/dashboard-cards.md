# Dashboard Cards

Ready-made Lovelace markdown card templates for Krowi Energy Management.

---

## Gas price breakdown

```yaml
type: markdown
content: >
  {% set spot = states('sensor.gas_spot_today_price') | float(0) %} {% set t =
  states('number.gas_tariff_transport') | float(0) %} {% set d =
  states('number.gas_tariff_distribution') | float(0) %} {% set e =
  states('number.gas_tariff_excise_duty') | float(0) %} {% set c =
  states('number.gas_tariff_energy_contribution') | float(0) %} {% set surcharge
  = states('sensor.gas_tariff_total_surcharge') | float(0) %} {% set vat =
  states('number.gas_vat') | float(0) %} {% set pre_vat = (spot + surcharge) |
  round(5) %} {% set price = states('sensor.gas_current_price') | float(0) %}


  **Gas price breakdown (c€/kWh)**


  **Surcharges:**

  - {{ state_attr('number.gas_tariff_transport', 'friendly_name') }}: **{{
  '%.5f' | format(t) }}**

  - {{ state_attr('number.gas_tariff_distribution', 'friendly_name') }}: **{{
  '%.5f' | format(d) }}**

  - {{ state_attr('number.gas_tariff_excise_duty', 'friendly_name') }}: **{{
  '%.5f' | format(e) }}**

  - {{ state_attr('number.gas_tariff_energy_contribution', 'friendly_name') }}:
  **{{ '%.5f' | format(c) }}**


  **Total surcharge: {{ '%.5f' | format(surcharge) }}**


  **Spot:**

  - {{ state_attr('sensor.gas_spot_today_price', 'friendly_name') }}: **{{
  '%.5f' | format(spot) }}**



  **Pre-VAT: {{ '%.5f' | format(pre_vat) }}**

  × {{ (1 + vat / 100) | round(4) }} (VAT {{ vat }}%)


  ---


  **Current gas price: {{ '%.5f' | format(price) }} c€/kWh**
```

---

## Electricity import price breakdown

```yaml
type: markdown
content: >
  {% set spot = states('sensor.electricity_spot_current_price') | float(0) %} {%
  set g = states('number.electricity_tariff_green_energy_contribution') |
  float(0) %} {% set dt =
  states('number.electricity_tariff_distribution_transport') | float(0) %} {%
  set ex = states('number.electricity_tariff_excise_duty') | float(0) %} {% set
  ec = states('number.electricity_tariff_energy_contribution') | float(0) %} {%
  set surcharge = states('sensor.electricity_tariff_total_surcharge') | float(0)
  %} {% set vat = states('number.electricity_vat') | float(0) %} {% set pre_vat
  = (spot + surcharge) | round(5) %} {% set price =
  states('sensor.electricity_current_price_import') | float(0) %}


  **Electricity import price breakdown (c€/kWh)**


  **Surcharges:**

  - {{ state_attr('number.electricity_tariff_green_energy_contribution',
  'friendly_name') }}: **{{ '%.5f' | format(g) }}**

  - {{ state_attr('number.electricity_tariff_distribution_transport',
  'friendly_name') }}: **{{ '%.5f' | format(dt) }}**

  - {{ state_attr('number.electricity_tariff_excise_duty', 'friendly_name') }}:
  **{{ '%.5f' | format(ex) }}**

  - {{ state_attr('number.electricity_tariff_energy_contribution',
  'friendly_name') }}: **{{ '%.5f' | format(ec) }}**


  **Total surcharge: {{ '%.5f' | format(surcharge) }}**


  **Spot:**

  - {{ state_attr('sensor.electricity_spot_current_price', 'friendly_name') }}:
  **{{ '%.5f' | format(spot) }}**


  **Pre-VAT: {{ '%.5f' | format(pre_vat) }}**

  × {{ (1 + vat / 100) | round(4) }} (VAT {{ vat }}%)


  ---


  **Current import price: {{ '%.5f' | format(price) }} c€/kWh**
```

---

## Electricity export price

> This card reflects the **default** export price formula: `spot_avg × 0.94 − 1.7 c€/kWh`. If you changed the export template in the integration options, adjust the formula variables below accordingly.

```yaml
type: markdown
content: >
  {% set avg = states('sensor.electricity_spot_average_price') | float(0) %} {% set
  factor = 0.94 %} {% set deduction = 1.7 %} {% set pre_deduction = (avg * factor) |
  round(5) %} {% set price = states('sensor.electricity_current_price_export') | float(0)
  %}


  **Electricity export price (c€/kWh)**


  **Spot:**

  - {{ state_attr('sensor.electricity_spot_average_price', 'friendly_name') }}: **{{
  '%.5f' | format(avg) }}**


  **Formula:**

  - Injection factor: **× {{ factor }}** → {{ '%.5f' | format(pre_deduction) }}

  - Fixed deduction: **− {{ deduction }} c€/kWh**


  {{ '%.5f' | format(pre_deduction) }} − {{ deduction }}

  **= {{ '%.5f' | format(price) }} c€/kWh**


  ---


  **Current export price: {{ '%.5f' | format(price) }} c€/kWh**
```

---

## Net electricity cost

```yaml
type: markdown
content: >
  {% set import_cost = states('sensor.electricity_total_import_cost') | float(0) %}
  {% set export_revenue = states('sensor.electricity_total_export_revenue') | float(0)
  %} {% set net = states('sensor.electricity_net_cost') | float(0) %}


  **Net electricity cost (EUR)**


  **Import:**

  - {{ state_attr('sensor.electricity_total_import_cost', 'friendly_name') }}: **{{
  '%.2f' | format(import_cost) }} EUR**


  **Export:**

  - {{ state_attr('sensor.electricity_total_export_revenue', 'friendly_name') }}: **{{
  '%.2f' | format(export_revenue) }} EUR**


  {{ '%.2f' | format(import_cost) }} − {{ '%.2f' | format(export_revenue) }}

  **= {{ '%.2f' | format(net) }} EUR**


  ---


  **Net cost: {{ '%.2f' | format(net) }} EUR**
```
