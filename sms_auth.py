
import json
import os
import random
import string
import time
from datetime import datetime, timedelta

SMS_CODES_FILE = 'sms_codes.json'
USER_SESSIONS_FILE = 'user_sessions.json'

def load_sms_codes():
    """Загружает коды SMS из файла"""
    if os.path.exists(SMS_CODES_FILE):
        try:
            with open(SMS_CODES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_sms_codes(codes):
    """Сохраняет коды SMS в файл"""
    with open(SMS_CODES_FILE, 'w', encoding='utf-8') as f:
        json.dump(codes, f, ensure_ascii=False, indent=2)

def load_user_sessions():
    """Загружает пользовательские сессии"""
    if os.path.exists(USER_SESSIONS_FILE):
        try:
            with open(USER_SESSIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_user_sessions(sessions):
    """Сохраняет пользовательские сессии"""
    with open(USER_SESSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

def generate_sms_code():
    """Генерирует 4-значный SMS код"""
    return ''.join(random.choices(string.digits, k=4))

def send_sms_code(phone):
    """
    Отправляет SMS код на указанный номер телефона
    В тестовой версии просто сохраняет код в памяти
    """
    # Очищаем номер телефона от лишних символов
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Проверяем лимит отправки (не более 3 SMS в час)
    codes = load_sms_codes()
    current_time = datetime.now()
    
    # Проверяем количество отправленных SMS за последний час
    hour_ago = current_time - timedelta(hours=1)
    recent_codes = [
        code_data for code_data in codes.values() 
        if (code_data.get('phone') == clean_phone and 
            datetime.fromisoformat(code_data.get('created_at', '2020-01-01')) > hour_ago)
    ]
    
    if len(recent_codes) >= 3:
        return {
            'success': False,
            'message': 'Слишком много попыток. Попробуйте через час.'
        }
    
    # Генерируем новый код
    sms_code = generate_sms_code()
    code_id = f"{clean_phone}_{int(time.time())}"
    
    # Сохраняем код (действует 10 минут)
    codes[code_id] = {
        'phone': clean_phone,
        'code': sms_code,
        'created_at': current_time.isoformat(),
        'expires_at': (current_time + timedelta(minutes=10)).isoformat(),
        'used': False
    }
    
    save_sms_codes(codes)
    
    # В реальной системе здесь был бы запрос к SMS API
    print(f"📱 SMS код для {clean_phone}: {sms_code}")
    print(f"⏰ Код действует 10 минут")
    
    return {
        'success': True,
        'message': f'SMS код отправлен на номер {clean_phone}',
        'test_code': sms_code,  # Только для тестирования!
        'phone': clean_phone
    }

def verify_sms_code(phone, entered_code):
    """Проверяет введенный SMS код"""
    clean_phone = ''.join(filter(str.isdigit, phone))
    codes = load_sms_codes()
    current_time = datetime.now()
    
    # Ищем активный код для этого номера
    for code_id, code_data in codes.items():
        if (code_data.get('phone') == clean_phone and 
            code_data.get('code') == entered_code and 
            not code_data.get('used', False)):
            
            # Проверяем, не истек ли код
            expires_at = datetime.fromisoformat(code_data.get('expires_at'))
            if current_time > expires_at:
                return {
                    'success': False,
                    'message': 'Код истек. Запросите новый код.'
                }
            
            # Отмечаем код как использованный
            codes[code_id]['used'] = True
            codes[code_id]['verified_at'] = current_time.isoformat()
            save_sms_codes(codes)
            
            # Создаем пользовательскую сессию
            session_token = create_user_session(clean_phone)
            
            return {
                'success': True,
                'message': 'Код подтвержден!',
                'session_token': session_token,
                'phone': clean_phone
            }
    
    return {
        'success': False,
        'message': 'Неверный код или код уже использован.'
    }

def create_user_session(phone):
    """Создает сессию для пользователя"""
    sessions = load_user_sessions()
    session_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    
    sessions[session_token] = {
        'phone': phone,
        'created_at': datetime.now().isoformat(),
        'last_activity': datetime.now().isoformat()
    }
    
    save_user_sessions(sessions)
    return session_token

def get_user_by_session(session_token):
    """Получает пользователя по токену сессии"""
    if not session_token:
        return None
        
    sessions = load_user_sessions()
    session_data = sessions.get(session_token)
    
    if not session_data:
        return None
    
    # Проверяем, не истекла ли сессия (30 дней)
    last_activity = datetime.fromisoformat(session_data.get('last_activity'))
    if datetime.now() - last_activity > timedelta(days=30):
        # Удаляем истекшую сессию
        del sessions[session_token]
        save_user_sessions(sessions)
        return None
    
    # Обновляем время последней активности
    sessions[session_token]['last_activity'] = datetime.now().isoformat()
    save_user_sessions(sessions)
    
    return {
        'phone': session_data['phone'],
        'session_token': session_token
    }

def logout_user(session_token):
    """Выход пользователя из системы"""
    if not session_token:
        return False
        
    sessions = load_user_sessions()
    if session_token in sessions:
        del sessions[session_token]
        save_user_sessions(sessions)
        return True
    
    return False

def cleanup_expired_codes():
    """Очищает истекшие SMS коды"""
    codes = load_sms_codes()
    current_time = datetime.now()
    
    # Удаляем коды старше 1 часа
    hour_ago = current_time - timedelta(hours=1)
    codes_to_remove = []
    
    for code_id, code_data in codes.items():
        created_at = datetime.fromisoformat(code_data.get('created_at', '2020-01-01'))
        if created_at < hour_ago:
            codes_to_remove.append(code_id)
    
    for code_id in codes_to_remove:
        del codes[code_id]
    
    if codes_to_remove:
        save_sms_codes(codes)
        print(f"🧹 Очищено {len(codes_to_remove)} истекших SMS кодов")
