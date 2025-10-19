import math


def get_input(prompt, default):
    """Helper function: get user input with a default value."""
    val = input(f"{prompt} [{default}]: ").strip()
    return float(val) if val else default


def main():
    print(
        "=== Expected Equity Return Calculator ===\n(Press Enter to use default values)\n"
    )

    # --- Inputs with defaults ---
    current_cape = get_input("Enter current CAPE", 22)
    long_term_cape = get_input("Enter long-term mean CAPE", 20)
    g_real = get_input("Enter expected real GDP growth rate (%)", 1.5) / 100
    inflation = get_input("Enter expected inflation rate (%)", 2.1) / 100
    dilution = get_input("Enter expected annual share dilution (%)", 0.5) / 100
    years = get_input("Enter CAPE mean reversion in years", 10)
    risk_free = get_input("Enter risk-free rate (%)", 2.5) / 100

    # --- Calculations ---
    cape_contribution = (math.log(long_term_cape) - math.log(current_cape)) / years
    expected_equity_nominal = (
        (1 / current_cape) + (g_real + inflation - dilution) + cape_contribution
    )
    expected_equity_real = expected_equity_nominal - inflation
    erp = expected_equity_nominal - risk_free

    # --- Results ---
    print("\n=== Results ===")
    print(f"CAPE contribution: {cape_contribution * 100:.2f}% per year")
    print(
        f"Expected nominal equity return: {expected_equity_nominal * 100:.2f}% per year"
    )
    print(f"Expected real equity return: {expected_equity_real * 100:.2f}% per year")
    print(f"Equity risk premium (ERP): {erp * 100:.2f}% per year")


if __name__ == "__main__":
    main()
