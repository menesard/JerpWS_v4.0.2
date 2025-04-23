from flask_login import UserMixin

from app import db
from datetime import datetime
import pytz
from app.utils.helpers import convert_utc_to_local
from flask import g

# İşlem türleri için sabitler
OPERATION_ADD = 'ADD'
OPERATION_SUBTRACT = 'SUBTRACT'

def get_current_time():
    """GMT+3 (Türkiye) zaman diliminde şu anki zamanı döndürür"""
    return datetime.now(pytz.timezone('Europe/Istanbul'))


class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10), unique=True, nullable=False)
    purity_per_thousand = db.Column(db.Integer, nullable=False, default=916)  # Varsayılan değer 22 ayar için
    active_setting = db.Column(db.Boolean, default=False)  # Aktif ayar olup olmadığını belirten alan
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time)

    def __init__(self, name, purity_per_thousand=916, active_setting=False):
        super().__init__()
        self.name = name
        self.purity_per_thousand = purity_per_thousand
        self.active_setting = active_setting

    def __repr__(self):
        return f"<Setting {self.name}>"

    @classmethod
    def init_default_settings(cls):
        """Varsayılan ayarları oluştur"""
        default_settings = [
            {'name': '8', 'purity': 333},
            {'name': '14', 'purity': 585},
            {'name': '18', 'purity': 750},
            {'name': '21', 'purity': 875},
            {'name': '22', 'purity': 916},
            {'name': '24', 'purity': 995}
        ]

        for setting_data in default_settings:
            existing = cls.query.filter_by(name=setting_data['name']).first()
            if not existing:
                new_setting = cls(
                    name=setting_data['name'],
                    purity_per_thousand=setting_data['purity'],
                    active_setting=False
                )
                db.session.add(new_setting)
        
        db.session.commit()


class GlobalSetting(db.Model):
    __tablename__ = 'global_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def __repr__(self):
        return f"<GlobalSetting {self.key}>"


class Region(db.Model):
    __tablename__ = 'regions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)  # Bölgenin aktif/silindi durumu
    is_default = db.Column(db.Boolean, default=False)  # Varsayılan bölge mi?
    created_at = db.Column(db.DateTime, default=get_current_time)

    def __repr__(self):
        return f"<Region {self.name}>"

class Operation(db.Model):
    __tablename__ = 'operations'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=get_current_time, nullable=False)
    operation_type = db.Column(db.String(20), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    source_region_id = db.Column(db.Integer, db.ForeignKey('regions.id'))
    target_region_id = db.Column(db.Integer, db.ForeignKey('regions.id'))
    setting_id = db.Column(db.Integer, db.ForeignKey('settings.id'), nullable=False)
    gram = db.Column(db.Float, nullable=False)


    # İlişkiler

    source_region = db.relationship('Region', foreign_keys=[source_region_id])
    target_region = db.relationship('Region', foreign_keys=[target_region_id])
    setting = db.relationship('Setting')
    user = db.relationship('User', backref=db.backref('operations', lazy='dynamic'))

    def __repr__(self):
        return f"<Operation {self.operation_type} {self.gram}g>"


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default='staff')
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=get_current_time)

    # İlişkiler
    created_by = db.relationship('User', remote_side=[id], backref=db.backref('created_users', lazy='dynamic'))

    def can_access_region(self, region_name):
        """Kullanıcının belirli bir bölgeye erişim yetkisi olup olmadığını kontrol eder"""
        if self.is_admin:
            return True
        if self.role == 'staff':
            # Görevliler masa ve yer bölgelerine erişemez
            return region_name not in ['masa', 'table', 'yer']
        return True

    def has_role(self, role):
        if self.is_admin:
            return True
        if role == 'manager' and self.role == 'manager':
            return True
        if role == 'staff' and (self.role == 'manager' or self.role == 'staff'):
            return True
        return False

class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=get_current_time)

    # İlişkiler
    customer_transactions = db.relationship('CustomerTransaction',
                                            back_populates='customer',
                                            lazy='dynamic',
                                            cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Customer {self.name}>"

# İşlem türleri için sabitler
TRANSACTION_PRODUCT_IN = 'PRODUCT_IN'
TRANSACTION_PRODUCT_OUT = 'PRODUCT_OUT'
TRANSACTION_SCRAP_IN = 'SCRAP_IN'
TRANSACTION_SCRAP_OUT = 'SCRAP_OUT'


class CustomerTransaction(db.Model):
    __tablename__ = 'customer_transactions'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    transaction_date = db.Column(db.DateTime, default=get_current_time)
    product_description = db.Column(db.String(200))
    setting_id = db.Column(db.Integer, db.ForeignKey('settings.id'), nullable=False)
    gram = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float)
    labor_cost = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float)
    purity_per_thousand = db.Column(db.Integer, default=916)
    pure_gold_weight = db.Column(db.Float)
    labor_percentage = db.Column(db.Float, default=0)
    labor_pure_gold = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    used_in_transfer = db.Column(db.Boolean, default=False, nullable=False)
    transfer_id = db.Column(db.Integer, db.ForeignKey('transfers.id'), nullable=True)

    # İlişkiler
    customer = db.relationship('Customer',
                               back_populates='customer_transactions',
                               foreign_keys=[customer_id])

    setting = db.relationship('Setting')
    transfer = db.relationship('Transfer', backref='transactions')

    # Düzenleme ile ilgili yeni alanlar
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by = db.relationship('User', foreign_keys=[created_by_user_id])

    is_edited = db.Column(db.Boolean, default=False)
    edited_date = db.Column(db.DateTime)
    edited_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    edited_by = db.relationship('User', foreign_keys=[edited_by_user_id])

    original_transaction_id = db.Column(db.Integer, db.ForeignKey('customer_transactions.id'))
    original_transaction = db.relationship('CustomerTransaction',
                                           remote_side=[id],
                                           backref=db.backref('edited_versions', lazy='dynamic'),
                                           foreign_keys=[original_transaction_id])

    def __repr__(self):
        return f"<CustomerTransaction {self.transaction_type} {self.gram}g>"

    def get_transaction_type_tr(self):
        """İşlem türünün Türkçe karşılığını döndürür"""
        if self.transaction_type == TRANSACTION_PRODUCT_IN:
            return 'Ürün Girişi'
        elif self.transaction_type == TRANSACTION_PRODUCT_OUT:
            return 'Ürün Çıkışı'
        elif self.transaction_type == TRANSACTION_SCRAP_IN:
            return 'Hurda Girişi'
        elif self.transaction_type == TRANSACTION_SCRAP_OUT:
            return 'Hurda Çıkışı'
        else:
            return self.transaction_type # Bilinmeyen tür için orijinal değeri döndür

def init_db():
    """Veritabanını başlangıç verileriyle doldur"""
    # Varsayılan bölgeler
    default_regions = [
        {'name': 'kasa', 'is_default': True},
        {'name': 'yer', 'is_default': True}
    ]

    # Normal bölgeler
    normal_regions = []

    # Varsayılan bölgeleri ekle
    for region_data in default_regions:
        if not Region.query.filter_by(name=region_data['name']).first():
            region = Region(
                name=region_data['name'],
                is_default=region_data.get('is_default', False),
                is_active=True
            )
            db.session.add(region)
            print(f"Varsayılan bölge eklendi: {region_data['name']}")

    # Normal bölgeleri ekle
    for region_name in normal_regions:
        if not Region.query.filter_by(name=region_name).first():
            region = Region(
                name=region_name,
                is_default=False,
                is_active=True
            )
            db.session.add(region)


    settings_data = [
        {'name': '8', 'purity_per_thousand': 333},
        {'name': '14', 'purity_per_thousand': 585},
        {'name': '18', 'purity_per_thousand': 750},
        {'name': '21', 'purity_per_thousand': 875},
        {'name': '22', 'purity_per_thousand': 916}
    ]

    for setting_data in settings_data:
        if not Setting.query.filter_by(name=setting_data['name']).first():
            setting = Setting(name=setting_data['name'],
                              purity_per_thousand=setting_data['purity_per_thousand'])
            db.session.add(setting)
            print(f"Ayar eklendi: {setting_data['name']}")

    # Admin kullanıcı
    if not User.query.filter_by(username='admin').first():
        from werkzeug.security import generate_password_hash
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin'),
            is_admin=True,
            role='admin'
        )
        db.session.add(admin)
        print("Admin kullanıcı eklendi")

    try:
        db.session.commit()
        print("Veritabanına başlangıç verileri başarıyla eklendi")
    except Exception as e:
        db.session.rollback()
        print(f"Veritabanına veri eklerken hata: {e}")
        raise
class Fire(db.Model):
    __tablename__ = 'fires'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=get_current_time, nullable=False)
    expected_pure_gold = db.Column(db.Float, nullable=False)  # Beklenen has miktar
    actual_pure_gold = db.Column(db.Float, nullable=False)  # Gerçek has miktar
    fire_amount = db.Column(db.Float, nullable=False)  # Fire miktarı (has cinsinden)
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # İlişkiler
    user = db.relationship('User', backref=db.backref('fires', lazy='dynamic'))
    fire_details = db.relationship('FireDetail', backref='fire', lazy='dynamic')


class FireDetail(db.Model):
    __tablename__ = 'fire_details'

    id = db.Column(db.Integer, primary_key=True)
    fire_id = db.Column(db.Integer, db.ForeignKey('fires.id'), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=False)
    setting_id = db.Column(db.Integer, db.ForeignKey('settings.id'), nullable=False)
    gram = db.Column(db.Float, nullable=False)
    pure_gold = db.Column(db.Float, nullable=False)

    # İlişkiler
    region = db.relationship('Region')
    setting = db.relationship('Setting')


class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=get_current_time, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount_tl = db.Column(db.Float, default=0)  # TL cinsinden tutar
    amount_gold = db.Column(db.Float, default=0)  # Altın gram cinsinden tutar
    gold_price = db.Column(db.Float, default=0)  # İşlem günündeki altın fiyatı
    used_in_transfer = db.Column(db.Boolean, default=False)  # Devirde kullanıldı mı
    transfer_id = db.Column(db.Integer, db.ForeignKey('transfers.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # İlişkiler
    user = db.relationship('User')


class Transfer(db.Model):
    __tablename__ = 'transfers'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=get_current_time, nullable=False)
    customer_total = db.Column(db.Float, nullable=False)  # Müşteri işlemleri toplamı
    labor_total = db.Column(db.Float, nullable=False)  # İşçilik toplamı
    expense_total = db.Column(db.Float, nullable=False)  # Masraf toplamı
    transfer_amount = db.Column(db.Float, nullable=False)  # Devir miktarı
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # İlişkiler
    user = db.relationship('User')
    expenses = db.relationship('Expense', backref='transfer')


class DailyVault(db.Model):
    __tablename__ = 'daily_vaults'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=get_current_time().date, nullable=False)
    expected_total = db.Column(db.Float, nullable=False)  # Sistemde beklenen toplam
    actual_total = db.Column(db.Float, nullable=False)  # Girilen gerçek toplam
    difference = db.Column(db.Float, nullable=False)  # Fark
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)

    # İlişkiler
    user = db.relationship('User')
    details = db.relationship('DailyVaultDetail', backref='daily_vault', lazy='dynamic')


class DailyVaultDetail(db.Model):
    __tablename__ = 'daily_vault_details'

    id = db.Column(db.Integer, primary_key=True)
    daily_vault_id = db.Column(db.Integer, db.ForeignKey('daily_vaults.id'), nullable=False)
    setting_id = db.Column(db.Integer, db.ForeignKey('settings.id'), nullable=False)
    expected_gram = db.Column(db.Float, nullable=False)  # Sistemde beklenen
    actual_gram = db.Column(db.Float, nullable=False)  # Girilen gerçek

    # İlişkiler
    setting = db.relationship('Setting')


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=get_current_time)

    # İlişkiler
    outputs = db.relationship('ProductOutput', backref='product', lazy='dynamic')

    def __repr__(self):
        return f"<Product {self.name}>"


class ProductOutput(db.Model):
    __tablename__ = 'product_outputs'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=get_current_time, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    setting_id = db.Column(db.Integer, db.ForeignKey('settings.id'), nullable=False)
    weight = db.Column(db.Float, nullable=False)  # Gram cinsinden ağırlık
    purity = db.Column(db.Integer, nullable=False)  # Ayar değeri
    has_value = db.Column(db.Float, nullable=False)  # Has değer
    used_in_transfer = db.Column(db.Boolean, default=False)  # Devirde kullanıldı mı
    transfer_id = db.Column(db.Integer, db.ForeignKey('transfers.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # İlişkiler
    setting = db.relationship('Setting')
    user = db.relationship('User')
    transfer = db.relationship('Transfer', backref='product_outputs')

    def __repr__(self):
        return f"<ProductOutput {self.product.name} {self.weight}g>"


class BaseModel:
    def to_dict(self):
        """Model verilerini sözlüğe dönüştürür"""
        data = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Tarih alanlarını dönüştür
            if isinstance(value, datetime):
                # Her zaman GMT+3 (Türkiye) zaman dilimini kullan
                value = convert_utc_to_local(value, 'Europe/Istanbul')
            data[column.name] = value
        return data