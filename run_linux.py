#!/usr/bin/env python
import os
from app import create_app


application = create_app()

# Bu satır, 'python wsgi.py' ile çalıştırıldığında kullanılır
if __name__ == "__main__":
    """    
    # SSL sertifikalarını kontrol et
    cert_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ssl')
    ssl_context = None
    
    if os.path.exists(os.path.join(cert_dir, 'cert.pem')) and \
       os.path.exists(os.path.join(cert_dir, 'key.pem')):
        ssl_context = (
            os.path.join(cert_dir, 'cert.pem'),
            os.path.join(cert_dir, 'key.pem')
        )
        print("SSL sertifikaları bulundu, HTTPS kullanılacak")
    else:
        print("SSL sertifikaları bulunamadı, HTTP kullanılacak")
    """
    port = int(os.environ.get('PORT', 8080))
    application.run(
        host='0.0.0.0',
        port=port,
        debug=True,
        use_reloader=True,
        threaded=True
    )