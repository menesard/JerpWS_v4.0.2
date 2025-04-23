from app import create_app, db
from app.models.database import Setting

app = create_app()

with app.app_context():
    # 14 ayar ayarını bul
    setting = Setting.query.filter_by(name='14').first()
    if setting:
        # Milyem değerini güncelle
        setting.purity_per_thousand = 585
        db.session.commit()
        print("14 ayar milyem değeri 585 olarak güncellendi.")
    else:
        print("14 ayar bulunamadı.") 