# Mapeo de conceptos XBRL (us-gaap) a campos del proyecto

Orden = preferencia. Los nombres pueden cambiar con las versiones de la taxonomía us-gaap: **comprueba contra el 10-K real y la taxonomía vigente** antes de fiarte de un nombre. Si un concepto no aparece, prueba el siguiente de la lista.

## Cuenta de resultados (duración)

| Campo | Conceptos |
|---|---|
| revenue | `Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`, `RevenueFromContractWithCustomerIncludingAssessedTax`, `SalesRevenueNet` (antiguo) |
| cogs | `CostOfRevenue`, `CostOfGoodsAndServicesSold`, `CostOfGoodsSold` |
| gross_profit | `GrossProfit` |
| sga | `SellingGeneralAndAdministrativeExpense` |
| rnd | `ResearchAndDevelopmentExpense` |
| ebit (operating income) | `OperatingIncomeLoss` |
| interest_expense | `InterestExpense`, `InterestExpenseNonoperating`, `InterestExpenseDebt` |
| pretax_income | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest`, `IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments` |
| income_tax | `IncomeTaxExpenseBenefit` |
| net_income | `NetIncomeLoss`, `ProfitLoss` (incluye minoritarios) |
| eps_diluted | `EarningsPerShareDiluted` |
| diluted_shares_wavg | `WeightedAverageNumberOfDilutedSharesOutstanding` |
| effective_tax_rate | `EffectiveIncomeTaxRateContinuingOperations` |

## Balance (instante)

| Campo | Conceptos |
|---|---|
| cash | `CashAndCashEquivalentsAtCarryingValue`, `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` (incluye restringida; avisa) |
| st_investments | `ShortTermInvestments`, `MarketableSecuritiesCurrent`, `AvailableForSaleSecuritiesDebtSecuritiesCurrent` |
| accounts_receivable | `AccountsReceivableNetCurrent`, `ReceivablesNetCurrent` |
| inventory | `InventoryNet` |
| other_current_assets | `OtherAssetsCurrent`, `PrepaidExpenseAndOtherAssetsCurrent` |
| total_current_assets | `AssetsCurrent` |
| ppe_net | `PropertyPlantAndEquipmentNet` |
| total_assets | `Assets` |
| accounts_payable | `AccountsPayableCurrent`, `AccountsPayableAndAccruedLiabilitiesCurrent` |
| accrued_liabilities | `AccruedLiabilitiesCurrent` |
| deferred_revenue | `ContractWithCustomerLiabilityCurrent`, `DeferredRevenueCurrent` |
| total_current_liabilities | `LiabilitiesCurrent` |
| st_debt | `DebtCurrent`, `ShortTermBorrowings`, `LongTermDebtCurrent`, `CommercialPaper` |
| lt_debt | `LongTermDebtNoncurrent`, `LongTermDebt` (total; evita doble conteo con la parte corriente) |
| op_lease_liab_current | `OperatingLeaseLiabilityCurrent` |
| op_lease_liab_noncurrent | `OperatingLeaseLiabilityNoncurrent` |
| fin_lease_liab_current | `FinanceLeaseLiabilityCurrent` |
| fin_lease_liab_noncurrent | `FinanceLeaseLiabilityNoncurrent` |
| preferred | `PreferredStockValue`, `TemporaryEquityCarryingAmountAttributableToParent` |
| minority_interest | `MinorityInterest` |
| total_liabilities | `Liabilities` |
| total_equity | `StockholdersEquity`, `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` |
| retained_earnings | `RetainedEarningsAccumulatedDeficit` |
| liabilities_and_equity | `LiabilitiesAndStockholdersEquity` |

**Deuda:** si el 10-K reporta `LongTermDebt` (total) y `LongTermDebtNoncurrent` + `LongTermDebtCurrent`, usa una sola vía y comprueba que la suma coincide.

## Flujo de caja (duración)

| Campo | Conceptos |
|---|---|
| cfo | `NetCashProvidedByUsedInOperatingActivities` |
| capex | `PaymentsToAcquirePropertyPlantAndEquipment`, `PaymentsToAcquireProductiveAssets` (salida de caja, valor positivo) |
| da | `DepreciationDepletionAndAmortization`, `DepreciationAndAmortization`, `DepreciationAmortizationAndAccretionNet` |
| sbc | `ShareBasedCompensation`, `AllocatedShareBasedCompensationExpense` |
| change_ar | `IncreaseDecreaseInAccountsReceivable` (positivo = uso de caja) |
| change_inventory | `IncreaseDecreaseInInventories` |
| change_ap | `IncreaseDecreaseInAccountsPayable` (positivo = fuente de caja) |
| dividends_paid | `PaymentsOfDividends`, `PaymentsOfDividendsCommonStock` |
| buybacks | `PaymentsForRepurchaseOfCommonStock` |

**Atención:** en los conceptos `IncreaseDecrease...` el signo XBRL significa *aumento del activo/pasivo*, no *efecto en caja*. Para activos, un aumento reduce caja. Normaliza una vez y documenta.

## Compensación en acciones (para acciones diluidas)

Los nombres exactos varían por empresa y año; busca por patrón y verifica:

| Dato | Patrón de concepto |
|---|---|
| Opciones vivas (cantidad) | `ShareBasedCompensationArrangementByShareBasedPaymentAwardOptionsOutstandingNumber` |
| Precio medio de ejercicio | `ShareBasedCompensationArrangementByShareBasedPaymentAwardOptionsOutstandingWeightedAverageExercisePrice` |
| RSUs/PSUs no consolidadas | `ShareBasedCompensationArrangementByShareBasedPaymentAwardEquityInstrumentsOtherThanOptionsNonvestedNumber` |
| Acciones en circulación (portada) | `dei:EntityCommonStockSharesOutstanding` |

## Metadatos del documento (dei)

| Campo | Concepto |
|---|---|
| Fecha de cierre del ejercicio | `dei:DocumentPeriodEndDate` |
| Tipo de formulario | `dei:DocumentType` |
| Ticker | `dei:TradingSymbol` |
| CIK | `dei:EntityCentralIndexKey` |
| Código SIC | no está en dei; obténlo de EDGAR `submissions` (`sic`) |

## Registro de decisiones

Cada vez que mapees un concepto propio de una empresa, añade aquí una línea:

```
YYYY-MM-DD | TICKER | company:ConceptoPropio -> campo | motivo | 10-K de origen
```
