import serial
import time
import random
import threading
import logging
import os
import platform

logger = logging.getLogger(__name__)

# Sistem türüne göre varsayılan port belirleme
def get_default_port():
    return "COM3"  # Her zaman COM3'ü varsayılan port olarak kullan

# Kullanılabilir portları listele
def list_available_ports():
    try:
        import serial.tools.list_ports
        return [port.device for port in serial.tools.list_ports.comports()]
    except ImportError:
        logger.warning("serial.tools.list_ports modülü bulunamadı")
        return []


def process_scale_data(line):
    """Teraziden gelen veriyi işle ve gram değerini döndür"""
    try:
        line = line.strip()
        list_line = line.split(' ')

        if not list_line:
            return 0.0, False

        # Sadece gram değeri içeren satırları işle
        if 'g' in line:
            try:
                # Son iki elemanı kontrol et (sayı ve 'g')
                if len(list_line) >= 2 and list_line[-1] == 'g':
                    weight = float(list_line[-2])
                    return round(weight, 2), True
            except (ValueError, IndexError):
                logger.error("GRAM VERİSİ OKUNAMADI: %s", line)
                return 0.0, False
        return 0.0, False
    except Exception as e:
        logger.error("Terazi veri işleme hatası: %s", str(e))
        return 0.0, False


class Scale:
    def __init__(self, port=None, baudrate=9600, timeout=1, simulation_mode=False):
        # Port belirtilmemişse varsayılan portu kullan
        self.port = port or os.environ.get('SCALE_PORT', get_default_port())
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.last_weight = None  # None olarak başlat
        self.is_connected = False
        self.lock = threading.Lock()

        # Kullanılabilir portları göster
        available_ports = list_available_ports()
        if available_ports:
            logger.info("Kullanılabilir portlar: %s", available_ports)

        try:
            self.ser = serial.Serial(self.port, baudrate, timeout=timeout)
            time.sleep(2)  # Bağlantının kurulması için bekle
            self.is_connected = True
            logger.info("Terazi bağlantısı kuruldu: %s", self.port)
        except Exception as e:
            logger.error("Terazi bağlantı hatası: %s", str(e))
            self.is_connected = False

    def _send_command(self, command):
        """Teraziye komut gönder"""
        if self.is_connected and self.ser:
            try:
                self.ser.write(command.encode() + b'\r\n')
                return True
            except Exception as e:
                logger.error("Terazi komut gönderme hatası: %s", str(e))
        return False

    def _read_response(self):
        """Teraziden yanıt oku"""
        if self.is_connected and self.ser:
            try:
                return self.ser.read_all().decode().strip()
            except Exception as e:
                logger.error("Terazi yanıt okuma hatası: %s", str(e))
        return ""

    def get_weight(self):
        """Teraziden ağırlık bilgisini al"""
        with self.lock:
            if self.is_connected and self.ser:
                response = self._read_response()
                if response:
                    weight, valid = process_scale_data(response)
                    if valid:
                        self.last_weight = weight  # Geçerli değeri kaydet
                        return weight, True

            # Bağlantı yok veya veri okunamadı, son geçerli değeri döndür
            if self.last_weight is None:
                return 0.0, False  # Hiç geçerli değer alınmadıysa 0.0 döndür
            return self.last_weight, False

    def close(self):
        """Terazi bağlantısını kapat"""
        if self.is_connected and self.ser:
            try:
                self.ser.close()
                self.is_connected = False
                logger.info("Terazi bağlantısı kapatıldı")
                return True
            except Exception as e:
                logger.error("Terazi bağlantısı kapatılırken hata: %s", str(e))
        return False


class ScaleManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ScaleManager, cls).__new__(cls)
            cls._instance.scale = None
            cls._instance.callbacks = []
            cls._instance.running = False
            cls._instance.thread = None
            cls._instance.weight = 0.0
            cls._instance.is_valid = False
        return cls._instance

    def initialize(self, port="COM3", baudrate=9600, simulation_mode=False):
        """Terazi bağlantısını başlat"""
        self.scale = Scale(port, baudrate, simulation_mode=simulation_mode)
        return self.scale.is_connected or simulation_mode

    def start_monitoring(self, interval=0.2):
        """Terazi değerlerini sürekli izlemeyi başlat"""
        if self.running or not self.scale:
            return False

        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.thread.daemon = True
        self.thread.start()
        logger.info("Terazi izleme başlatıldı")
        return True

    def stop_monitoring(self):
        """Terazi izlemeyi durdur"""
        if not self.running:
            return False

        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        logger.info("Terazi izleme durduruldu")
        return True

    def _monitor_loop(self, interval):
        """Terazi değerlerini periyodik olarak oku"""
        while self.running and self.scale:
            self.weight, self.is_valid = self.scale.get_weight()

            # Callback fonksiyonlarını çağır
            for callback in self.callbacks:
                try:
                    callback(self.weight, self.is_valid)
                except Exception as e:
                    logger.error("Terazi callback hatası: %s", str(e))

            time.sleep(interval)

    def register_callback(self, callback):
        """Ağırlık değişiminde çağrılacak fonksiyonu kaydet"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            return True
        return False

    def unregister_callback(self, callback):
        """Callback fonksiyonunu kaldır"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            return True
        return False

    def get_current_weight(self):
        """Son okunan ağırlığı döndür"""
        return self.weight, self.is_valid

    def close(self):
        """Terazi bağlantısını kapat"""
        self.stop_monitoring()
        if self.scale:
            return self.scale.close()
        return False