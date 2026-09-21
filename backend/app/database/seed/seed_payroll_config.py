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
        config = PayrollConfig(pf_rate_percent=12.0, pf_wage_ceiling=15000.0, esi_rate_percent=0.75,
                                esi_wage_threshold=21000.0, pt_state="Unspecified", pt_amount=200.0, overtime_rate_multiplier=1.5)
        db.add(config)
        db.commit()
        print("Seeded PayrollConfig with PLACEHOLDER rates. Update before running real payroll.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
