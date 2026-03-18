# ECB Data Guide

## Resumen
El **Banco Central Europeo (BCE/ECB)** publica estadísticas macroeconómicas del Área Euro a través de su Statistical Data Warehouse (SDW). Este es el repositorio central para datos de política monetaria, inflación, tipos de interés, y actividad económica de la zona euro.

## Conceptos Clave

### Dataset (Dataflow)
Un **dataset** es un conjunto de series relacionadas temáticamente. El ECB tiene ~100 datasets.

| Dataset | Nombre | Qué contiene |
|---------|--------|--------------|
| **ICP** | HICP (Inflation) | Índice de Precios al Consumo Armonizado |
| **FM** | Financial Markets | Tipos de interés, Euribor, tipos de cambio |
| **BSI** | Balance Sheet Items | Agregados monetarios (M1, M2, M3), crédito |
| **MNA** | National Accounts | PIB, componentes del gasto |
| **LFSI** | Labour Force | Desempleo, empleo |
| **EXR** | Exchange Rates | Tipos de cambio EUR vs otras monedas |
| **BOP** | Balance of Payments | Balanza de pagos |
| **MIR** | Interest Rates | Tipos de interés bancarios (depósitos, préstamos) |

### Series Key (Clave de Serie)
Cada serie tiene un identificador único llamado **series key**, compuesto por valores de dimensiones separados por puntos.

Ejemplo: `M.U2.N.000000.4.INX`
```
M       .U2      .N          .000000   .4      .INX
│        │        │           │         │        │
FREQ    REF_AREA ADJUSTMENT  ICP_ITEM  UNIT    SUFFIX
Mensual Euro Area No ajust.  Todos     Índice  Index
```

### Dimensiones Comunes

| Dimensión | Descripción | Valores frecuentes |
|-----------|-------------|-------------------|
| **FREQ** | Frecuencia temporal | A=Anual, Q=Trimestral, M=Mensual, D=Diario |
| **REF_AREA** | Área geográfica | U2=Euro Area, DE=Alemania, ES=España, FR=Francia |
| **ADJUSTMENT** | Ajuste estacional | N=Sin ajustar, Y=Ajustado, S=SWDA |

### Códigos de País (REF_AREA)
| Código | País |
|--------|------|
| U2 | Euro Area (agregado) |
| DE | Alemania |
| ES | España |
| FR | Francia |
| IT | Italia |
| NL | Países Bajos |
| BE | Bélgica |
| AT | Austria |
| PT | Portugal |
| IE | Irlanda |
| GR | Grecia |
| FI | Finlandia |

## Datos más solicitados

### 1. Inflación (HICP)
- **Dataset**: ICP
- **Serie clave Euro Area**: `M.U2.N.000000.4.INX` (HICP headline YoY)
- **Core inflation**: `M.U2.N.XEF000.4.INX` (excluyendo energía y alimentos)
- **Por país**: Cambiar U2 por código país (ej: `M.DE.N.000000.4.INX` para Alemania)

### 2. Tipos de Interés ECB
- **Dataset**: FM
- **Deposit Facility Rate (DFR)**: `B.U2.EUR.4F.KR.DFR.LEV` - Tipo principal desde 2022
- **Main Refinancing Operations (MRO)**: `B.U2.EUR.4F.KR.MRO.LEV`
- **Marginal Lending Facility (MLF)**: `B.U2.EUR.4F.KR.MLFR.LEV`

### 3. Euribor
- **Dataset**: FM
- **Euribor 3 meses**: `M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA`
- **Euribor 12 meses**: `M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA`

### 4. Agregados Monetarios
- **Dataset**: BSI
- **M3 Euro Area**: `M.U2.Y.V.M30.X.I.U2.2300.Z01.E`
- **M1 Euro Area**: `M.U2.Y.V.M10.X.I.U2.2300.Z01.E`

### 5. PIB
- **Dataset**: MNA
- **PIB Euro Area YoY**: `Q.Y.I8.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.N12`
- **PIB Euro Area QoQ**: `Q.Y.I8.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.GY`

### 6. Desempleo
- **Dataset**: LFSI
- **Tasa de paro Euro Area**: `M.I8.S.UNEHRT.TOTAL0.15_74.T`

## Cómo usar los tools

### Paso 1: Explorar datasets
```
explore_datasets("inflation")
→ Encontrará el dataset ICP
```

### Paso 2: Ver dimensiones del dataset
```
explore_dimensions("ICP")
→ Mostrará: FREQ, REF_AREA, ADJUSTMENT, ICP_ITEM, STS_INSTITUTION, ICP_SUFFIX
```

### Paso 3: Buscar códigos
```
explore_codes("CL_AREA", "spain")
→ Encontrará: ES = Spain
```

### Paso 4: Construir y obtener serie
```
build_series(
    dataset="ICP",
    dimensions={
        "FREQ": "M",
        "REF_AREA": "ES",
        "ADJUSTMENT": "N",
        "ICP_ITEM": "000000",
        "STS_INSTITUTION": "4",
        "ICP_SUFFIX": "INX"
    },
    start_period="2020-01"
)
```

## Tips

1. **Series curadas**: Para las series más comunes, usa `search_series()` y `get_series()` que acceden al catálogo curado con IDs simples como `ecb_hicp_ea_yoy`.

2. **Frecuencias**: La mayoría de datos macro son mensuales (M) o trimestrales (Q). Los tipos del ECB son diarios pero tienen agregados mensuales.

3. **Ajuste estacional**: Usa `N` (Not adjusted) para datos oficiales sin ajustar, `Y` para ajustados.

4. **Última observación**: Los datos se publican con retraso. Inflación ~3 semanas, PIB ~45 días.

5. **Euro Area vs países**: U2 es el agregado Euro Area. Para datos por país, usar código ISO (DE, ES, FR...).

## Enlaces útiles
- Portal de datos: https://data.ecb.europa.eu
- Documentación API: https://data.ecb.europa.eu/help/api/data
- Explorador de series: https://data.ecb.europa.eu/data/datasets
