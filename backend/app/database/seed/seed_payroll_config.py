"""
Seeds a single PayrollConfig row with PLACEHOLDER statutory rates.

⚠️ These numbers are commonly-cited standard rates as a starting point,
NOT verified against your company's actual PF/ESI registration status,
applicable state, or current government notifications. Update via
PATCH /api/v1/payroll/config (requires payroll:manage) before running
real payroll -- do not pay anyone based on these defaults.

Run after seed_rbac.py:
    python -m app.database.seed.seed_payroll_config
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.database.connection.database import SessionLocal
from app.database.models.payroll import PayrollConfig


def main():
    db = SessionLocal()
    try:
        existing = db.query(PayrollConfig).first()
        if existing is not None:
            print("PayrollConfig already exists -- skipping (use the API to update it instead).")
            return

        config = PayrollConfig(
            pf_rate_percent=12.0,       # PLACEHOLDER -- standard employee-side EPF rate
            pf_wage_ceiling=15000.0,    # PLACEHOLDER -- commonly cited statutory wage ceiling
            esi_rate_percent=0.75,      # PLACEHOLDER -- standard employee-side ESI rate
            esi_wage_threshold=21000.0, # PLACEHOLDER -- commonly cited ESI applicability threshold
            pt_state="Unspecified",     # PLACEHOLDER -- PT is state-specific, set the real state
            pt_amount=200.0,            # PLACEHOLDER -- varies significantly by state and income slab
            overtime_rate_multiplier=1.5,
        )
        db.add(config)
        db.commit()
        print("Seeded PayrollConfig with PLACEHOLDER rates. Update before running real payroll.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
