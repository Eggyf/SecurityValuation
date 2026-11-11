"""Mapeo de conceptos XBRL a campos normalizados (AGENTS.md §6).

Este módulo es la fuente de verdad para la traducción de tags XBRL
(estándar us-gaap o extensiones de la empresa) a los campos de los
estados financieros normalizados.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Mapeo: concepto XBRL (lowercase) → campo normalizado
# ---------------------------------------------------------------------------

# Cuenta de resultados
INCOME_STATEMENT_MAP: Final[dict[str, str]] = {
    # Ingresos
    "revenues": "revenue",
    "revenuefromcontractwithcustomerexcludingassessedtax": "revenue",
    "salesrevenuenet": "revenue",
    "revenuefromcontractswithcustomers": "revenue",
    # COGS
    "costofgoodsandservicessold": "cogs",
    "costofrevenue": "cogs",
    "costofgoodssold": "cogs",
    # Gross Profit
    "grossprofit": "gross_profit",
    # SG&A
    "sellinggeneralandadministrativeexpense": "sga",
    "sellingandmarketingexpense": "sga",
    "generalandadministrativeexpense": "sga",
    # R&D
    "researchanddevelopmentexpense": "rd",
    "researchanddevelopmentexpensesoftwareexcludingacquiredinprocesscost": "rd",
    # D&A (P&L)
    "depreciationandamortization": "depreciation_amortization",
    "depreciationdepletionandamortization": "depreciation_amortization",
    # EBIT (Operating Income)
    "operatingincomeloss": "ebit",
    "incomefromoperations": "ebit",
    # Intereses
    "interestexpense": "interest_expense",
    "interestexpensegross": "interest_expense",
    "interestincomeexpensenet": "interest_expense",
    # Beneficio antes de impuestos
    "incomelossfromcontinuingoperationsbeforeincometaxesextraordinaryitemsnoncontrollinginterest": "pretax_income",  # noqa: E501
    "incomelossfromcontinuingoperationsbeforeincometaxes": "pretax_income",
    "earningsbeforetax": "pretax_income",
    # Impuestos
    "incometaxexpensebenefit": "income_tax_expense",
    "provisionforincometaxes": "income_tax_expense",
    # Beneficio neto
    "netincomeloss": "net_income",
    "netincome": "net_income",
    "profitloss": "net_income",
    # EPS diluido
    "earningspersharediluted": "diluted_eps",
    # Acciones diluidas
    "weightedaveragenumberofdilutedsharesoutstanding": "diluted_weighted_shares",
    # SBC
    "sharebasedcompensation": "sbc",
    "allocatedsharebasedcompensationexpense": "sbc",
}

# Balance
BALANCE_SHEET_MAP: Final[dict[str, str]] = {
    # Caja
    "cashandcashequivalentsatcarryingvalue": "cash_and_equivalents",
    "cash": "cash_and_equivalents",
    "cashcashequivalentsandshortterminvestments": "cash_and_equivalents",
    # Inversiones CP
    "shortterminvestments": "short_term_investments",
    "availableforsalesecuritiescurrent": "short_term_investments",
    "marketablesecuritiescurrent": "short_term_investments",
    # Cuentas por cobrar
    "accountsreceivablenetcurrent": "accounts_receivable",
    "receivablesnetcurrent": "accounts_receivable",
    # Inventario
    "inventorynet": "inventory",
    "inventoryfinishedgoods": "inventory",
    # Otros activos corrientes
    "otherassetscurrent": "other_current_assets",
    "prepaidexpenseandotherassetscurrent": "other_current_assets",
    # Cuentas por pagar
    "accountspayablecurrent": "accounts_payable",
    "accountspayableandaccruedliabilitiescurrent": "accounts_payable",
    # Pasivos acumulados
    "accruedliabilitiescurrent": "accrued_liabilities",
    "accruedexpensesandothercurrentliabilities": "accrued_liabilities",
    # Ingresos diferidos
    "deferredrevenuecurrent": "deferred_revenue",
    "contractwithcustomerliabilitycurrent": "deferred_revenue",
    "unearnedrevenue": "deferred_revenue",
    # Deuda CP
    "longtermdebtcurrent": "short_term_debt",
    "debtcurrent": "short_term_debt",
    "shorttermdebt": "short_term_debt",
    "currentportionoflongtermdebt": "short_term_debt",
    # Deuda LP
    "longtermdebtnoncurrent": "long_term_debt",
    "longtermdebt": "long_term_debt",
    # Leases operativos CP
    "operatingleaseliabilitycurrent": "operating_lease_liabilities_current",
    # Leases operativos LP
    "operatingleaseliabilitynoncurrent": "operating_lease_liabilities_noncurrent",
    # Leases financieros
    "financeleaseliability": "finance_lease_liabilities",
    "capitalleaseliability": "finance_lease_liabilities",
    # Acciones preferentes
    "preferredstockvalue": "preferred_stock",
    "preferredstock": "preferred_stock",
    # Intereses minoritarios
    "minorityinterest": "non_controlling_interest",
    "noncontrollinginterest": "non_controlling_interest",
    # Patrimonio
    "stockholdersequity": "total_equity",
    "stockholders Equity": "total_equity",
    # Totales
    "assets": "total_assets",
    "liabilities": "total_liabilities",
}

# Flujo de caja
CASH_FLOW_MAP: Final[dict[str, str]] = {
    # CFO
    "netcashprovidedbyusedinoperatingactivities": "cfo",
    "cashflowfromoperatingactivities": "cfo",
    "netcashprovidedbyoperatingactivities": "cfo",
    # CapEx
    "paymentstoacquirepropertyplantandequipment": "capex",
    "capitalExpenditures": "capex",
    "paymentstoacquireproductiveassets": "capex",
    # D&A (en flujo de caja)
    "depreciationdepletionandamortization": "depreciation_amortization",
    "depreciationandamortization": "depreciation_amortization",
    # SBC (en flujo de caja)
    "sharebasedcompensation": "sbc",
    "allocatedsharebasedcompensationexpense": "sbc",
    # Variación de caja
    "cashcashequivalentsrestrictedcashandrestrictedcashequivalentsperiodincreasedecreaseincludingexchangerateeffect": "net_change_in_cash",  # noqa: E501
    "netincreasein cash": "net_change_in_cash",
}

# Notas
NOTES_MAP: Final[dict[str, str]] = {
    # Opciones
    "sharebasedcompensationarrangementbysharebasedpaymentawardoptionsoutstandingnumber": "options_outstanding",  # noqa: E501
    "sharebasedcompensationarrangementbysharebasedpaymentawardoptionsoutstandingweightedaverageexerciseprice": "options_weighted_avg_exercise_price",  # noqa: E501
    # RSUs
    "sharebasedcompensationarrangementbysharebasedpaymentawardrsuoutstandingnumber": "rsus_outstanding",  # noqa: E501
    # Tasa impositiva
    "effectivetaxrate": "effective_tax_rate",
    "statutorytaxrate": "statutory_tax_rate",
}


def normalize_concept(concept: str) -> str:
    """Normaliza un concepto XBRL para búsqueda en el mapeo.

    Elimina espacios, guiones y convierte a minúsculas.
    """
    return concept.lower().replace(" ", "").replace("-", "").replace("_", "")


def map_concept(concept: str, statement_type: str) -> str | None:
    """Mapea un concepto XBRL a un campo normalizado.

    Args:
        concept: concepto XBRL (p. ej. "us-gaap:Revenues").
        statement_type: tipo de estado ("income", "balance", "cashflow", "notes").

    Returns:
        Nombre del campo normalizado, o None si no hay mapeo.
    """
    # Extraer el nombre local del concepto (después de ':')
    local_name = concept.split(":")[-1] if ":" in concept else concept
    normalized = normalize_concept(local_name)

    if statement_type == "income":
        return INCOME_STATEMENT_MAP.get(normalized)
    elif statement_type == "balance":
        return BALANCE_SHEET_MAP.get(normalized)
    elif statement_type == "cashflow":
        return CASH_FLOW_MAP.get(normalized)
    elif statement_type == "notes":
        return NOTES_MAP.get(normalized)
    return None


def is_company_extension(concept: str) -> bool:
    """Indica si el concepto es una extensión de la empresa (no us-gaap)."""
    prefix = concept.split(":")[0].lower() if ":" in concept else ""
    return prefix not in ("us-gaap", "dei", "srt", "xbrli", "xbrldi")


__all__ = [
    "BALANCE_SHEET_MAP",
    "CASH_FLOW_MAP",
    "INCOME_STATEMENT_MAP",
    "NOTES_MAP",
    "is_company_extension",
    "map_concept",
    "normalize_concept",
]
