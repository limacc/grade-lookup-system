from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_cors import CORS
import json
import os
from datetime import datetime
import logging

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 실제 운영에서는 환경변수로 설정
CORS(app)

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# 설정 파일 경로
CONFIG_FILE = 'config.json'
GRADES_FILE = 'grades.json'

def load_config():
    """설정을 로드합니다."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'expiry_date': None}

def save_config(config):
    """설정을 저장합니다."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def load_grades():
    """성적 데이터를 로드합니다."""
    if os.path.exists(GRADES_FILE):
        with open(GRADES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def is_expired():
    """조회 기간이 만료되었는지 확인합니다."""
    config = load_config()
    if not config.get('expiry_date'):
        return False
    
    try:
        expiry_date = datetime.strptime(config['expiry_date'], '%Y-%m-%d %H:%M')
        return datetime.now() > expiry_date
    except:
        return False

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/admin')
def admin():
    """관리자 페이지"""
    config = load_config()
    return render_template('admin.html', expiry_date=config.get('expiry_date', ''))

@app.route('/api/search', methods=['POST'])
def search_grade():
    """성적 조회 API"""
    try:
        # 만료 여부 확인
        if is_expired():
            app.logger.warning("만료된 접근 시도")
            return jsonify({
                'success': False,
                'message': '조회 기간이 종료되었습니다.'
            }), 400
        
        # 요청 데이터 검증
        if not request.is_json:
            app.logger.error("JSON이 아닌 요청")
            return jsonify({
                'success': False,
                'message': '잘못된 요청 형식입니다.'
            }), 400
            
        data = request.get_json()
        if not data:
            app.logger.error("빈 JSON 요청")
            return jsonify({
                'success': False,
                'message': '요청 데이터가 없습니다.'
            }), 400
        
        student_id = data.get('student_id', '').strip()
        name = data.get('name', '').strip()
        
        app.logger.info(f"성적 조회 요청: 학번={student_id}, 성명={name}")
        
        if not student_id or not name:
            app.logger.warning("빈 입력값 요청")
            return jsonify({
                'success': False,
                'message': '학번과 성명을 모두 입력해주세요.'
            }), 400
        
        # 입력값 검증
        if not student_id.isdigit() or len(student_id) != 9:
            app.logger.warning(f"잘못된 학번 형식: {student_id}")
            return jsonify({
                'success': False,
                'message': '올바른 9자리 학번을 입력해주세요.'
            }), 400
        
        if not name.replace(' ', '').isalpha() or len(name) < 2 or len(name) > 10:
            app.logger.warning(f"잘못된 성명 형식: {name}")
            return jsonify({
                'success': False,
                'message': '올바른 성명을 입력해주세요.'
            }), 400
        
        # 성적 데이터 로드
        try:
            grades = load_grades()
            app.logger.info(f"성적 데이터 로드 완료: {len(grades)}명")
        except Exception as e:
            app.logger.error(f"성적 데이터 로드 실패: {e}")
            return jsonify({
                'success': False,
                'message': '성적 데이터를 불러올 수 없습니다.'
            }), 500
        
        # 학번과 성명이 모두 일치하는 학생 찾기
        for student in grades:
            if student.get('student_id') == student_id and student.get('name') == name:
                app.logger.info(f"성적 조회 성공: {student_id} {name}")
                return jsonify({
                    'success': True,
                    'data': {
                        'student_id': student['student_id'],
                        'name': student['name'],
                        'grade': student['grade']
                    }
                })
        
        app.logger.warning(f"학생 정보 불일치: {student_id} {name}")
        return jsonify({
            'success': False,
            'message': '입력하신 정보와 일치하는 학생을 찾을 수 없습니다.'
        }), 404
        
    except Exception as e:
        app.logger.error(f"성적 조회 중 예외 발생: {type(e).__name__}: {e}")
        import traceback
        app.logger.error(f"상세 오류: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'서버 오류가 발생했습니다. 관리자에게 문의해주세요.'
        }), 500

@app.route('/api/admin/set-expiry', methods=['POST'])
def set_expiry():
    """만료일 설정 API"""
    try:
        data = request.get_json()
        expiry_date = data.get('expiry_date', '').strip()
        
        if not expiry_date:
            return jsonify({
                'success': False,
                'message': '만료일을 입력해주세요.'
            }), 400
        
        # 날짜 형식 검증
        try:
            datetime.strptime(expiry_date, '%Y-%m-%d %H:%M')
        except ValueError:
            return jsonify({
                'success': False,
                'message': '올바른 날짜 형식(YYYY-MM-DD HH:MM)을 입력해주세요.'
            }), 400
        
        # 설정 저장
        config = load_config()
        config['expiry_date'] = expiry_date
        save_config(config)
        
        return jsonify({
            'success': True,
            'message': '만료일이 설정되었습니다.'
        })
        
    except Exception as e:
        app.logger.error(f"만료일 설정 중 오류 발생: {e}")
        return jsonify({
            'success': False,
            'message': '서버 오류가 발생했습니다.'
        }), 500

@app.route('/api/status')
def status():
    """시스템 상태 확인 API"""
    config = load_config()
    grades_count = len(load_grades())
    
    return jsonify({
        'expiry_date': config.get('expiry_date'),
        'is_expired': is_expired(),
        'grades_count': grades_count
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
