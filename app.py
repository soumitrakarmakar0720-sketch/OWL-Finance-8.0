import os, json, hmac, hashlib, base64, uuid, calendar, re, secrets, time
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from cryptography.fernet import Fernet, InvalidToken
load_dotenv()
app=Flask(__name__)
app.secret_key=os.getenv('SECRET_KEY','dev-only-change-me')
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('PUBLIC_BASE_URL','').startswith('https://'),MAX_CONTENT_LENGTH=int(os.getenv('MAX_UPLOAD_MB','8'))*1024*1024)
dburl=os.getenv('DATABASE_URL','sqlite:///local.db')
if dburl.startswith('postgres://'): dburl=dburl.replace('postgres://','postgresql+psycopg://',1)
if dburl.startswith('postgresql://'): dburl=dburl.replace('postgresql://','postgresql+psycopg://',1)
app.config['SQLALCHEMY_DATABASE_URI']=dburl
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
db=SQLAlchemy(app)
CASHFREE_ENV=os.getenv('CASHFREE_ENV','sandbox').strip().lower()
if CASHFREE_ENV not in ('sandbox','production'): raise RuntimeError('CASHFREE_ENV must be sandbox or production')
LIVE=CASHFREE_ENV=='production'
UPLOAD=Path(os.getenv('UPLOAD_DIR',str(Path(__file__).parent/'uploads')))
UPLOAD.mkdir(parents=True,exist_ok=True)
class User(db.Model):
 id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(150),nullable=False); email=db.Column(db.String(200),unique=True,nullable=False); password=db.Column(db.String(255),nullable=False); role=db.Column(db.String(20),default='customer'); phone=db.Column(db.String(20)); created=db.Column(db.DateTime,default=datetime.utcnow)
class Application(db.Model):
 id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); amount=db.Column(db.Numeric(14,2),nullable=False); purpose=db.Column(db.String(500),nullable=False); dob=db.Column(db.String(20)); address=db.Column(db.Text); pan_last4=db.Column(db.String(4)); aadhaar_last4=db.Column(db.String(4)); bank_last4=db.Column(db.String(4)); bank_name=db.Column(db.String(120)); ifsc=db.Column(db.String(20)); employment=db.Column(db.String(100)); monthly_income=db.Column(db.Numeric(14,2)); status=db.Column(db.String(30),default='submitted'); kyc_status=db.Column(db.String(30),default='pending'); admin_note=db.Column(db.Text); created=db.Column(db.DateTime,default=datetime.utcnow); user=db.relationship('User')
class SensitiveKYC(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 application_id=db.Column(db.Integer,db.ForeignKey('application.id'),unique=True,nullable=False)
 pan_encrypted=db.Column(db.Text,nullable=False)
 aadhaar_encrypted=db.Column(db.Text,nullable=False)
 bank_account_encrypted=db.Column(db.Text,nullable=False)
 account_holder_encrypted=db.Column(db.Text,nullable=False)

class GuestOTP(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 phone=db.Column(db.String(20),nullable=False,index=True)
 code_hash=db.Column(db.String(255),nullable=False)
 expires=db.Column(db.DateTime,nullable=False)
 attempts=db.Column(db.Integer,default=0)
 created=db.Column(db.DateTime,default=datetime.utcnow)

class Foreclosure(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 loan_id=db.Column(db.Integer,db.ForeignKey('loan.id'),nullable=False)
 amount=db.Column(db.Numeric(14,2),nullable=False)
 status=db.Column(db.String(25),default='requested',nullable=False)
 requested_at=db.Column(db.DateTime,default=datetime.utcnow)
 reviewed_at=db.Column(db.DateTime)
 admin_note=db.Column(db.Text)
 loan=db.relationship('Loan')

class Document(db.Model):
 id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('application.id'),nullable=False); kind=db.Column(db.String(30),nullable=False); filename=db.Column(db.String(300),nullable=False); original_name=db.Column(db.String(200)); created=db.Column(db.DateTime,default=datetime.utcnow)
class Loan(db.Model):
 id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('application.id'),unique=True,nullable=False); principal=db.Column(db.Numeric(14,2),nullable=False); annual_or_monthly=db.Column(db.String(10),nullable=False); rate=db.Column(db.Numeric(8,3),nullable=False); method=db.Column(db.String(12),nullable=False); tenure=db.Column(db.Integer,nullable=False); emi=db.Column(db.Numeric(14,2),nullable=False); total=db.Column(db.Numeric(14,2),nullable=False); status=db.Column(db.String(25),default='offered'); accepted_at=db.Column(db.DateTime); disbursed_at=db.Column(db.DateTime); created=db.Column(db.DateTime,default=datetime.utcnow); application=db.relationship('Application')
class DisbursementRecord(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 loan_id=db.Column(db.Integer,db.ForeignKey('loan.id'),unique=True,nullable=False)
 method=db.Column(db.String(20),nullable=False)
 reference=db.Column(db.String(120),unique=True,nullable=False)
 amount=db.Column(db.Numeric(14,2),nullable=False)
 transfer_date=db.Column(db.Date,nullable=False)
 recorded_at=db.Column(db.DateTime,default=datetime.utcnow,nullable=False)
 recorded_by=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
 note=db.Column(db.Text)
 loan=db.relationship('Loan')

class Installment(db.Model):
 id=db.Column(db.Integer,primary_key=True); loan_id=db.Column(db.Integer,db.ForeignKey('loan.id'),nullable=False); number=db.Column(db.Integer,nullable=False); due_date=db.Column(db.Date,nullable=False); amount=db.Column(db.Numeric(14,2),nullable=False); paid=db.Column(db.Numeric(14,2),default=0); __table_args__=(UniqueConstraint('loan_id','number'),)
class Payment(db.Model):
 id=db.Column(db.Integer,primary_key=True); installment_id=db.Column(db.Integer,db.ForeignKey('installment.id'),nullable=False); order_id=db.Column(db.String(100),unique=True,nullable=False); amount=db.Column(db.Numeric(14,2),nullable=False); status=db.Column(db.String(25),default='pending'); cf_payment_id=db.Column(db.String(100)); created=db.Column(db.DateTime,default=datetime.utcnow)
class Audit(db.Model):
 id=db.Column(db.Integer,primary_key=True); actor_id=db.Column(db.Integer); action=db.Column(db.String(100)); subject=db.Column(db.String(100)); detail=db.Column(db.Text); created=db.Column(db.DateTime,default=datetime.utcnow)
def encrypt_sensitive(value):
 key=os.getenv('KYC_ENCRYPTION_KEY','')
 if not key: raise RuntimeError('KYC_ENCRYPTION_KEY must be configured in Render before accepting applications')
 return Fernet(key.strip().encode()).encrypt(value.encode()).decode()

def decrypt_sensitive(value):
 return Fernet(os.environ['KYC_ENCRYPTION_KEY'].strip().encode()).decrypt(value.encode()).decode()

def valid_phone(value): return bool(re.fullmatch(r'[6-9][0-9]{9}',value or ''))

def loan_access(l):
 u=user()
 return bool((u and (u.role=='admin' or l.application.user_id==u.id)) or (session.get('guest_phone')==l.application.user.phone and session.get('guest_until',0)>time.time()))

def money(v): return Decimal(str(v)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
def audit(action,subject,detail=''):
 db.session.add(Audit(actor_id=session.get('uid'),action=action,subject=subject,detail=detail))
def user(): return db.session.get(User,session['uid']) if session.get('uid') else None
@app.context_processor
def context(): return dict(me=user(),live=LIVE,public_lookup=os.getenv('PUBLIC_PHONE_LOOKUP_ENABLED','false').lower()=='true')
def login_required(role=None):
 def outer(fn):
  @wraps(fn)
  def inner(*a,**kw):
   u=user()
   if not u: return redirect(url_for('login'))
   if role and u.role!=role: abort(403)
   return fn(*a,**kw)
  return inner
 return outer
@app.before_request
def csrf_check():
 if request.method in ('POST','PUT','PATCH','DELETE') and request.endpoint!='cashfree_webhook':
  if not hmac.compare_digest(str(session.get('csrf','')),str(request.form.get('csrf',request.headers.get('X-CSRF-Token','')))) or not session.get('csrf'): abort(400,'Invalid CSRF token')
@app.context_processor
def csrf():
 if 'csrf' not in session: session['csrf']=uuid.uuid4().hex
 return {'csrf':session['csrf']}
@app.route('/')
def home(): return redirect(url_for('dashboard')) if user() else render_template('public_home.html')
@app.route('/register',methods=['GET','POST'])
def register():
 if request.method=='POST':
  email=request.form['email'].strip().lower(); pw=request.form['password']
  if len(pw)<10: flash('Use a password of at least 10 characters.'); return redirect(url_for('register'))
  if User.query.filter_by(email=email).first(): flash('Email already registered.'); return redirect(url_for('register'))
  u=User(name=request.form['name'].strip(),email=email,phone=request.form['phone'].strip(),password=generate_password_hash(pw)); db.session.add(u); db.session.commit(); session.clear(); session['uid']=u.id; return redirect(url_for('dashboard'))
 return render_template('auth.html',register=True)
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  u=User.query.filter_by(email=request.form['email'].strip().lower()).first()
  if u and check_password_hash(u.password,request.form['password']): session.clear(); session['uid']=u.id; return redirect(url_for('dashboard'))
  flash('Invalid login details.')
 return render_template('auth.html',register=False)
@app.post('/logout')
def logout(): session.clear(); return redirect(url_for('login'))
@app.route('/dashboard')
@login_required()
def dashboard():
 u=user()
 if u.role in ('admin','staff'):
  return render_template('admin.html',applications=Application.query.order_by(Application.created.desc()).all(),loans=Loan.query.order_by(Loan.created.desc()).all(),auditlogs=Audit.query.order_by(Audit.created.desc()).limit(15).all())
 apps=Application.query.filter_by(user_id=u.id).order_by(Application.created.desc()).all()
 loans=Loan.query.join(Application).filter(Application.user_id==u.id).all()
 return render_template('dashboard.html',applications=apps,loans=loans)
@app.route('/apply',methods=['GET','POST'])
@login_required('customer')
def apply():
 if request.method=='POST':
  try:
   amount=money(request.form['amount']); income=money(request.form['income'])
   if amount<=0 or income<0: raise ValueError()
  except Exception: flash('Enter valid amounts.'); return redirect(url_for('apply'))
  pan=request.form.get('pan_full','').strip().upper(); aadhaar=re.sub(r'\s+','',request.form.get('aadhaar_full','')); bank=re.sub(r'\s+','',request.form.get('bank_account_full','')); holder=request.form.get('account_holder','').strip()
  if not re.fullmatch(r'[A-Z]{5}[0-9]{4}[A-Z]',pan) or not re.fullmatch(r'[0-9]{12}',aadhaar) or not re.fullmatch(r'[0-9]{6,18}',bank) or not holder or len(holder)>150:
   flash('Check the full PAN, Aadhaar and bank account details.'); return redirect(url_for('apply'))
  try:
   Fernet(os.environ.get('KYC_ENCRYPTION_KEY','').strip().encode())
  except (ValueError, KeyError, TypeError):
   app.logger.error('KYC_ENCRYPTION_KEY invalid: generate a Fernet key and set it in Render')
   flash('Loan application cannot be saved: KYC encryption is not configured. Please contact the administrator.'); return redirect(url_for('apply'))
  a=Application(user_id=user().id,amount=amount,purpose=request.form['purpose'][:500],dob=request.form['dob'],address=request.form['address'],pan_last4=pan[-4:],aadhaar_last4=aadhaar[-4:],bank_last4=bank[-4:],bank_name=request.form['bank_name'],ifsc=request.form['ifsc'],employment=request.form['employment'],monthly_income=income)
  db.session.add(a); db.session.flush()
  db.session.add(SensitiveKYC(application_id=a.id,pan_encrypted=encrypt_sensitive(pan),aadhaar_encrypted=encrypt_sensitive(aadhaar),bank_account_encrypted=encrypt_sensitive(bank),account_holder_encrypted=encrypt_sensitive(holder)))
  kinds=['photo','pan','aadhaar','bank_proof','income_proof']
  for kind in kinds:
   f=request.files.get(kind)
   if not f or not f.filename: db.session.rollback(); flash('All five document uploads are required.'); return redirect(url_for('apply'))
   ext=Path(secure_filename(f.filename)).suffix.lower()
   if ext not in ('.pdf','.png','.jpg','.jpeg','.webp'): db.session.rollback(); flash('Only PDF and image files are allowed.'); return redirect(url_for('apply'))
   head=f.stream.read(16); f.stream.seek(0)
   valid=(ext=='.pdf' and head.startswith(b'%PDF-')) or (ext=='.png' and head.startswith(b'\x89PNG\r\n\x1a\n')) or (ext in ('.jpg','.jpeg') and head.startswith(b'\xff\xd8\xff')) or (ext=='.webp' and head[:4]==b'RIFF' and head[8:12]==b'WEBP')
   if not valid: db.session.rollback(); flash('Document contents do not match the selected file type.'); return redirect(url_for('apply'))
   name=f'{uuid.uuid4().hex}{ext}'; f.save(UPLOAD/name); db.session.add(Document(application_id=a.id,kind=kind,filename=name,original_name=secure_filename(f.filename)))
  audit('application_submitted',f'application:{a.id}'); db.session.commit(); flash('Application submitted for manual verification.'); return redirect(url_for('dashboard'))
 return render_template('apply.html')
@app.route('/admin/application/<int:aid>')
@login_required('admin')
def review(aid):
 a=db.get_or_404(Application,aid); loan=Loan.query.filter_by(application_id=aid).first(); docs=Document.query.filter_by(application_id=aid).all(); return render_template('review.html',a=a,docs=docs,loan=loan)
@app.route('/document/<int:did>')
@login_required()
def document(did):
 d=db.get_or_404(Document,did); a=db.get_or_404(Application,d.application_id)
 if user().role not in ('admin','staff') and a.user_id!=user().id: abort(403)
 return send_file(UPLOAD/Path(d.filename).name,as_attachment=True,download_name=d.original_name)
@app.post('/admin/application/<int:aid>/kyc')
@login_required('admin')
def kyc(aid):
 a=db.get_or_404(Application,aid); status=request.form['status']
 if status not in ('verified','rejected','correction_requested'): abort(400)
 a.kyc_status=status; a.admin_note=request.form.get('note','')[:2000]
 if status=='rejected': a.status='rejected'
 audit('kyc_'+status,f'application:{aid}',a.admin_note); db.session.commit(); return redirect(url_for('review',aid=aid))
def calc(principal,rate,rate_type,method,tenure):
 r=Decimal(str(rate))/(Decimal('100') if rate_type=='monthly' else Decimal('1200')); p=money(principal)
 if method=='flat': total=money(p*(1+r*tenure)); emi=money(total/tenure)
 else:
  emi=money(p/tenure if r==0 else p*r*(1+r)**tenure/((1+r)**tenure-1)); total=money(emi*tenure)
 return emi,total
@app.post('/admin/application/<int:aid>/offer')
@login_required('admin')
def offer(aid):
 a=db.get_or_404(Application,aid)
 if a.kyc_status!='verified' or Loan.query.filter_by(application_id=aid).first(): abort(400,'KYC must be verified; only one offer per application.')
 try:
  p=money(request.form['principal']); rate=Decimal(request.form['rate']); tenure=int(request.form['tenure']); rt=request.form['rate_type']; method=request.form['method']
  if not (p.is_finite() and rate.is_finite() and p>0 and Decimal(0)<=rate<=Decimal(60) and 1<=tenure<=120 and rt in ('monthly','annual') and method in ('flat','reducing')): raise ValueError()
  emi,total=calc(p,rate,rt,method,tenure)
 except Exception: abort(400,'Invalid loan terms')
 loan=Loan(application_id=aid,principal=p,rate=rate,annual_or_monthly=rt,method=method,tenure=tenure,emi=emi,total=total)
 db.session.add(loan); a.status='offered'; audit('loan_offered',f'application:{aid}',f'principal={p},rate={rate},type={rt},method={method},tenure={tenure}'); db.session.commit(); return redirect(url_for('review',aid=aid))
@app.post('/loan/<int:lid>/accept')
@login_required('customer')
def accept(lid):
 l=db.get_or_404(Loan,lid)
 if l.application.user_id!=user().id or l.status!='offered': abort(403)
 l.status='accepted'; l.accepted_at=datetime.utcnow(); l.application.status='accepted'; audit('offer_accepted',f'loan:{lid}'); db.session.commit(); return redirect(url_for('loan_detail',lid=lid))
def add_months(d,n):
 m=d.month-1+n; y=d.year+m//12; month=m%12+1; return date(y,month,min(d.day,calendar.monthrange(y,month)[1]))
@app.post('/admin/loan/<int:lid>/record-disbursement')
@login_required('admin')
def record_disbursement(lid):
 """Record an externally completed manual bank/UPI transfer. Does not initiate a payout."""
 l=db.get_or_404(Loan,lid)
 if l.status!='accepted': abort(409,'Only accepted loans may be recorded as disbursed.')
 if DisbursementRecord.query.filter_by(loan_id=lid).first() or Installment.query.filter_by(loan_id=lid).first(): abort(409,'Disbursement already recorded.')
 if request.form.get('confirmation')!='yes': abort(400,'Confirm the transfer has actually completed.')
 method=request.form.get('method','')
 reference=request.form.get('reference','').strip()
 transfer_date_str=request.form.get('transfer_date','')
 if method not in ('upi','bank_transfer') or not re.fullmatch(r'[A-Za-z0-9_./-]{6,120}',reference): abort(400,'Invalid transfer method or reference.')
 try: transfer_date=date.fromisoformat(transfer_date_str)
 except ValueError: abort(400,'Invalid transfer date.')
 if transfer_date>date.today(): abort(400,'Transfer date cannot be in the future.')
 if not l.application.kyc_status=='verified': abort(409,'KYC must be verified.')
 if not l.accepted_at: abort(409,'Borrower must accept the loan offer.')
 # No bank/UPI API is called here. Admin attests funds were transferred outside OWL FINANCE.
 record=DisbursementRecord(loan_id=lid,method=method,reference=reference,amount=l.principal,transfer_date=transfer_date,recorded_by=user().id,note=request.form.get('note','')[:1000])
 db.session.add(record)
 l.status='active'; l.disbursed_at=datetime.utcnow(); l.application.status='active'
 assigned=Decimal('0')
 for n in range(1,l.tenure+1):
  amt=l.emi if n<l.tenure else money(l.total-assigned)
  if amt<=0: abort(400,'Invalid installment schedule')
  assigned+=amt
  db.session.add(Installment(loan_id=lid,number=n,due_date=add_months(transfer_date,n),amount=amt))
 audit('manual_disbursement_recorded',f'loan:{lid}',f'method={method}; reference={reference}; amount={l.principal}; transfer_date={transfer_date}')
 db.session.commit()
 flash('Manual disbursement recorded. Confirmed bank/UPI transfer was performed outside this website.')
 return redirect(url_for('loan_detail',lid=lid))

@app.route('/loan/<int:lid>')
@login_required()
def loan_detail(lid):
 l=db.get_or_404(Loan,lid)
 if not loan_access(l): abort(403)
 installments=Installment.query.filter_by(loan_id=lid).order_by(Installment.number).all()
 return render_template('loan.html',loan=l,installments=installments,foreclosure=Foreclosure.query.filter_by(loan_id=l.id).order_by(Foreclosure.id.desc()).first(),disbursement=DisbursementRecord.query.filter_by(loan_id=l.id).first())
def cashfree_base(): return 'https://api.cashfree.com/pg' if LIVE else 'https://sandbox.cashfree.com/pg'
def cashfree_headers(): return {'x-client-id':(os.getenv('CASHFREE_CLIENT_ID') or os.getenv('CASHFREE_APP_ID','')),'x-client-secret':os.getenv('CASHFREE_SECRET_KEY',''),'x-api-version':os.getenv('CASHFREE_API_VERSION','2025-01-01'),'Content-Type':'application/json'}
@app.post('/installment/<int:iid>/pay')
def pay(iid):
 ins=db.get_or_404(Installment,iid); l=db.get_or_404(Loan,ins.loan_id)
 if not loan_access(l) or (user() and user().role=='admin') or l.status not in ('active','demo_active'): abort(403)
 remaining=money(ins.amount-ins.paid)
 if remaining<=0: abort(400)
 if LIVE and not os.getenv('PUBLIC_BASE_URL','').startswith('https://'): abort(503,'Production checkout requires HTTPS PUBLIC_BASE_URL.')
 if not (os.getenv('CASHFREE_CLIENT_ID') or os.getenv('CASHFREE_APP_ID')) or not os.getenv('CASHFREE_SECRET_KEY'): flash('Cashfree has not been configured.'); return redirect(url_for('guest_loan',lid=l.id) if not user() else url_for('loan_detail',lid=l.id))
 oid='OWL'+uuid.uuid4().hex[:24]; payload={'order_id':oid,'order_amount':float(remaining),'order_currency':'INR','customer_details':{'customer_id':str(l.application.user.id),'customer_name':l.application.user.name,'customer_email':l.application.user.email,'customer_phone':l.application.user.phone},'order_meta':{'return_url':os.getenv('PUBLIC_BASE_URL','').rstrip('/')+url_for('payment_return',oid=oid),'notify_url':os.getenv('PUBLIC_BASE_URL','').rstrip('/')+url_for('cashfree_webhook')}}
 try:
  res=requests.post(cashfree_base()+'/orders',headers=cashfree_headers(),json=payload,timeout=15); res.raise_for_status(); data=res.json(); ps=data['payment_session_id']
 except Exception:
  app.logger.exception('Cashfree order creation failed: status=%s body=%s',res.status_code if 'res' in locals() else 'no-response',(res.text[:800] if 'res' in locals() else 'network failure'))
  flash('Payment gateway could not start. Please try again or contact support.'); return redirect(url_for('guest_loan',lid=l.id) if not user() else url_for('loan_detail',lid=l.id))
 db.session.add(Payment(installment_id=iid,order_id=oid,amount=remaining)); db.session.commit(); return render_template('checkout.html',payment_session_id=ps,env=CASHFREE_ENV)
@app.route('/payment/return/<oid>')
def payment_return(oid):
 p=Payment.query.filter_by(order_id=oid).first_or_404(); ins=db.get_or_404(Installment,p.installment_id); l=db.get_or_404(Loan,ins.loan_id)
 if not loan_access(l): abort(403)
 flash('Payment initiated. Final status is confirmed only after verified gateway notification.'); return redirect(url_for('guest_loan',lid=l.id) if not user() else url_for('loan_detail',lid=l.id))
@app.post('/webhooks/cashfree')
def cashfree_webhook():
 raw=request.get_data(); timestamp=request.headers.get('x-webhook-timestamp',''); signature=request.headers.get('x-webhook-signature',''); secret=os.getenv('CASHFREE_SECRET_KEY','')
 app.logger.info('Cashfree webhook received: timestamp_present=%s signature_present=%s content_type=%s body_length=%s',bool(timestamp),bool(signature),request.content_type,len(raw))
 if not secret or not timestamp or not signature:
  app.logger.warning('Cashfree webhook rejected: missing secret or signature headers')
  abort(401)
 digest=base64.b64encode(hmac.new(secret.encode(),timestamp.encode()+raw,hashlib.sha256).digest()).decode()
 if not hmac.compare_digest(digest,signature):
  app.logger.warning('Cashfree webhook rejected: invalid signature')
  abort(401)
 try:
  data=json.loads(raw)
 except (ValueError, TypeError):
  app.logger.warning('Cashfree webhook rejected: invalid JSON')
  abort(400)
 if not isinstance(data,dict): abort(400)
 event=data.get('type','')
 details=data.get('data')
 if not isinstance(details,dict) or not isinstance(details.get('payment'),dict) or not isinstance(details.get('order'),dict):
  # Cashfree endpoint-validation/test events may not contain a payment/order.
  # Acknowledge only after signature verification; never credit a payment.
  app.logger.info('Cashfree signed non-payment/test notification acknowledged: event=%s',str(event)[:100])
  return '',200
 payment=details['payment']; order=details['order']; oid=order.get('order_id')
 if not isinstance(oid,str) or not oid: abort(400,'Missing order ID')
 p=Payment.query.filter_by(order_id=oid).first()
 if not p: return '',200
 if p.status=='success': return '',200
 if not payment.get('cf_payment_id'): abort(400,'Missing Cashfree payment ID')
 if payment.get('payment_status')!='SUCCESS': return '',200
 if event and event!='PAYMENT_SUCCESS_WEBHOOK': return '',200
 if money(order.get('order_amount',0))!=money(p.amount) or order.get('order_currency')!='INR': abort(400)
 # The signed webhook is valid for the configured Cashfree environment.
 ins=db.get_or_404(Installment,p.installment_id)
 if money(ins.paid+p.amount)>money(ins.amount):
  audit('payment_overage_requires_review',f'payment:{p.id}',oid); p.status='review'; db.session.commit(); return '',200
 p.status='success'; p.cf_payment_id=str(payment.get('cf_payment_id','')); ins=db.get_or_404(Installment,p.installment_id); ins.paid=money(ins.paid+p.amount)
 loan=db.get_or_404(Loan,ins.loan_id)
 if all(money(i.paid)>=money(i.amount) for i in Installment.query.filter_by(loan_id=loan.id).all()): loan.status='closed'; loan.application.status='closed'
 audit('payment_verified',f'payment:{p.id}',oid); db.session.commit(); return '',200

# Public number-only lookup is DEMO-ONLY. Never use this flow with real borrower data.
# Keep guest access short-lived and limited to the repayment view; no KYC or profile access.
_guest_attempts={}
@app.route('/find-loan',methods=['GET','POST'])
def find_loan():
 if os.getenv('PUBLIC_PHONE_LOOKUP_ENABLED','false').lower()!='true': abort(403,'Public phone lookup is disabled until borrower verification is implemented.')
 if request.method=='POST':
  phone=request.form.get('phone','').strip()
  ip=(request.remote_addr or 'unknown')
  now=time.time()
  # Simple per-worker demo throttle; use Redis-backed limits before public production use.
  attempts=[t for t in _guest_attempts.get(ip,[]) if now-t<900]
  if len(attempts)>=12: abort(429,'Too many attempts. Please try later.')
  attempts.append(now); _guest_attempts[ip]=attempts
  if not valid_phone(phone):
   flash('Enter a valid 10-digit Indian mobile number.')
   return redirect(url_for('find_loan'))
  session['guest_phone']=phone
  session['guest_until']=now+600
  return redirect(url_for('guest_loans'))
 return render_template('find_loan.html')

@app.get('/my-loans-guest')
def guest_loans():
 if os.getenv('PUBLIC_PHONE_LOOKUP_ENABLED','false').lower()!='true': abort(403)
 phone=session.get('guest_phone')
 if not phone or session.get('guest_until',0)<=time.time():
  return redirect(url_for('find_loan'))
 loans=Loan.query.join(Application).join(User).filter(User.phone==phone,User.role=='customer').order_by(Loan.id.desc()).all()
 # This template intentionally excludes borrower identity, KYC and bank details.
 return render_template('guest_loans.html',loans=loans)

@app.get('/guest/loan/<int:lid>')
def guest_loan(lid):
 if os.getenv('PUBLIC_PHONE_LOOKUP_ENABLED','false').lower()!='true': abort(403)
 l=db.get_or_404(Loan,lid)
 if not session.get('guest_phone') or session.get('guest_until',0)<=time.time() or l.application.user.phone!=session['guest_phone']:
  abort(403)
 installments=Installment.query.filter_by(loan_id=l.id).order_by(Installment.number).all()
 return render_template('guest_loan.html',loan=l,installments=installments)

@app.post('/loan/<int:lid>/foreclosure-request')
def foreclosure_request(lid):
 l=db.get_or_404(Loan,lid)
 if not user() or (user().role!='admin' and l.application.user_id!=user().id) or l.status not in ('active','demo_active'): abort(403)
 if Foreclosure.query.filter(Foreclosure.loan_id==lid,Foreclosure.status.in_(['requested','approved'])).first(): abort(409,'Existing open foreclosure request')
 # Preliminary balance only; not a legally valid final foreclosure payoff.
 remaining=sum((money(i.amount-i.paid) for i in Installment.query.filter_by(loan_id=lid).all()),Decimal('0'))
 if remaining<=0: abort(400)
 db.session.add(Foreclosure(loan_id=lid,amount=money(remaining)))
 audit('foreclosure_requested',f'loan:{lid}','Preliminary quote based on remaining scheduled installments; not a final settlement figure')
 db.session.commit(); flash('Foreclosure request submitted for admin review. The amount is provisional.')
 return redirect(url_for('loan_detail',lid=lid))

@app.post('/admin/foreclosure/<int:fid>/decision')
@login_required('admin')
def foreclosure_decision(fid):
 f=db.get_or_404(Foreclosure,fid)
 if f.status!='requested': abort(409)
 decision=request.form.get('decision')
 if decision not in ('approved','rejected'): abort(400)
 f.status=decision; f.reviewed_at=datetime.utcnow(); f.admin_note=request.form.get('note','')[:1000]
 audit('foreclosure_'+decision,f'foreclosure:{fid}',f.admin_note)
 db.session.commit(); flash('Foreclosure decision saved.')
 return redirect(url_for('loan_detail',lid=f.loan_id))

@app.post('/admin/foreclosure/<int:fid>/settle')
@login_required('admin')
def settle_foreclosure(fid):
 f=db.get_or_404(Foreclosure,fid)
 l=db.get_or_404(Loan,f.loan_id)
 if f.status!='approved' or l.status!='active': abort(409,'Foreclosure must be approved and loan active.')
 if request.form.get('confirmation')!='yes': abort(400,'Confirm receipt of funds first.')
 reference=request.form.get('reference','').strip()
 if not re.fullmatch(r'[A-Za-z0-9_./-]{6,120}',reference): abort(400,'Enter a valid bank/UPI receipt reference.')
 if Audit.query.filter_by(action='foreclosure_settled',detail=reference).first(): abort(409,'Reference already recorded.')
 installments=Installment.query.filter_by(loan_id=l.id).order_by(Installment.number).all()
 outstanding=sum((money(i.amount-i.paid) for i in installments),Decimal('0'))
 if outstanding<=0: abort(409,'No outstanding installments.')
 try: received=money(request.form.get('amount',''))
 except Exception: abort(400,'Invalid received amount.')
 if received!=money(outstanding): abort(409,'Amount must match the current outstanding scheduled balance; revise the settlement agreement and accounting before accepting a different amount.')
 for i in installments:
  balance=money(i.amount-i.paid)
  if balance>0:
   db.session.add(Payment(installment_id=i.id,order_id='MANUAL-'+uuid.uuid4().hex,amount=balance,status='success',cf_payment_id='MANUAL:'+reference))
   i.paid=money(i.amount)
 l.status='closed';l.application.status='closed';f.status='settled';f.reviewed_at=datetime.utcnow()
 audit('foreclosure_settled',f'loan:{l.id}',reference)
 db.session.commit()
 flash('Foreclosure settlement recorded and loan closed. This records an externally verified payment; no transfer was initiated.')
 return redirect(url_for('loan_detail',lid=l.id))

@app.route('/admin/staff',methods=['GET','POST'])
@login_required('admin')
def staff_management():
 if request.method=='POST':
  email=request.form.get('email','').strip().lower(); pw=request.form.get('password','')
  if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or len(pw)<12 or User.query.filter_by(email=email).first():
   flash('Enter a unique valid email and a password of at least 12 characters.'); return redirect(url_for('staff_management'))
  db.session.add(User(name=request.form.get('name','').strip()[:150] or 'Staff',email=email,password=generate_password_hash(pw),role='staff',phone=request.form.get('phone','').strip()))
  audit('staff_created','staff:'+email); db.session.commit(); flash('Staff account created.'); return redirect(url_for('staff_management'))
 return render_template('staff.html',staff=User.query.filter_by(role='staff').all())

@app.post('/admin/customers/create')
@login_required()
def admin_create_customer():
 if user().role not in ('admin','staff'): abort(403)
 email=request.form.get('email','').strip().lower(); pw=request.form.get('password',''); phone=request.form.get('phone','').strip()
 if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or len(pw)<10 or not valid_phone(phone) or User.query.filter_by(email=email).first():
  flash('Valid unique email, Indian mobile number and 10+ character password required.'); return redirect(url_for('admin_customers'))
 u=User(name=request.form.get('name','').strip()[:150],email=email,phone=phone,password=generate_password_hash(pw),role='customer')
 if not u.name: abort(400)
 db.session.add(u); db.session.flush(); audit('customer_created',f'user:{u.id}'); db.session.commit()
 flash('Customer created.'); return redirect(url_for('admin_customers'))

@app.route('/admin/loans/new',methods=['GET','POST'])
@login_required('admin')
def admin_new_loan():
 if request.method=='POST':
  customer=db.session.get(User,int(request.form.get('customer_id',0)))
  if not customer or customer.role!='customer': abort(400)
  try:
   amount=money(request.form['principal']); rate=Decimal(request.form['rate']); tenure=int(request.form['tenure']); rt=request.form['rate_type']; method=request.form['method']
   if not amount.is_finite() or amount<=0 or not rate.is_finite() or not 0<=rate<=60 or not 1<=tenure<=120 or rt not in ('monthly','annual') or method not in ('flat','reducing'): raise ValueError()
   emi,total=calc(amount,rate,rt,method,tenure)
  except (ValueError,KeyError,ArithmeticError): abort(400,'Invalid loan terms')
  a=Application(user_id=customer.id,amount=amount,purpose=request.form.get('purpose','Admin-created loan')[:500],status='submitted',kyc_status='pending')
  db.session.add(a); db.session.flush()
  l=Loan(application_id=a.id,principal=amount,rate=rate,annual_or_monthly=rt,method=method,tenure=tenure,emi=emi,total=total,status='offered')
  db.session.add(l); db.session.flush(); audit('admin_created_loan',f'loan:{l.id}','KYC verification required before disbursement'); db.session.commit()
  flash('Loan offer created. Verify KYC and obtain customer acceptance before disbursement.'); return redirect(url_for('review',aid=a.id))
 return render_template('new_loan.html',customers=User.query.filter_by(role='customer').order_by(User.name).all())

@app.get('/admin/loans')
@login_required()
def admin_loans():
 if user().role not in ('admin','staff'): abort(403)
 status=request.args.get('status','active').strip().lower()
 allowed={'all','active','demo_active','offered','accepted','closed','foreclosed','cancelled'}
 if status not in allowed: abort(400,'Invalid loan filter')
 query=Loan.query
 if status=='active': query=query.filter(Loan.status.in_(['active','demo_active']))
 elif status!='all': query=query.filter(Loan.status==status)
 loans=query.order_by(Loan.created.desc()).all()
 return render_template('admin_loans.html',loans=loans,status=status)

@app.post('/admin/loan/<int:lid>/archive')
@login_required('admin')
def archive_loan(lid):
 l=db.get_or_404(Loan,lid)
 if l.status not in ('offered','accepted','cancelled'):
  abort(409,'Only undisbursed offers may be archived. Financial records must be retained.')
 if DisbursementRecord.query.filter_by(loan_id=lid).first() or Installment.query.filter_by(loan_id=lid).first():
  abort(409,'This loan has disbursement or installment records and cannot be archived.')
 if Foreclosure.query.filter_by(loan_id=lid).first():
  abort(409,'This loan has a foreclosure record and cannot be archived.')
 reason=request.form.get('reason','').strip()
 if len(reason)<8: abort(400,'Provide an archive reason of at least 8 characters.')
 l.status='cancelled'; l.application.status='cancelled'
 audit('loan_archived',f'loan:{lid}',reason[:500]); db.session.commit()
 flash('Undisbursed loan archived; financial history retained.')
 return redirect(url_for('admin_loans',status='all'))

@app.post('/admin/loan/<int:lid>/cancel')
@login_required('admin')
def cancel_loan(lid):
 l=db.get_or_404(Loan,lid)
 if l.status not in ('offered','accepted') or DisbursementRecord.query.filter_by(loan_id=lid).first() or Installment.query.filter_by(loan_id=lid).first(): abort(409,'Disbursed or repaid loans cannot be deleted. Use a closure workflow.')
 if Payment.query.join(Installment).filter(Installment.loan_id==lid).first(): abort(409)
 l.status='cancelled'; l.application.status='cancelled'; audit('loan_cancelled',f'loan:{lid}',request.form.get('reason','')[:500]); db.session.commit()
 flash('Loan cancelled and retained in audit history.'); return redirect(url_for('dashboard'))

@app.get('/admin/application/<int:aid>/sensitive')
@login_required('admin')
def view_sensitive_kyc(aid):
 a=db.get_or_404(Application,aid); record=SensitiveKYC.query.filter_by(application_id=aid).first_or_404()
 try:
  values={k:decrypt_sensitive(getattr(record,k+'_encrypted')) for k in ('pan','aadhaar','bank_account','account_holder')}
 except (InvalidToken,ValueError,KeyError):
  app.logger.exception('KYC decryption failed for application %s',aid); abort(503,'KYC key unavailable or mismatched; preserve original key.')
 audit('sensitive_kyc_viewed',f'application:{aid}'); db.session.commit()
 return render_template('sensitive_kyc.html',a=a,values=values),200,{'Cache-Control':'no-store','Pragma':'no-cache'}

@app.get('/health')
def health(): return jsonify(status='ok')

@app.get('/admin/customers')
@login_required()
def admin_customers():
 if user().role not in ('admin','staff'): abort(403)
 customers=User.query.filter_by(role='customer').order_by(User.created.desc()).all()
 return render_template('customers.html',customers=customers)

@app.get('/admin/payments')
@login_required('admin')
def admin_payments():
 payments=Payment.query.order_by(Payment.created.desc()).limit(250).all()
 return render_template('payments.html',payments=payments)

@app.get('/admin/report')
@login_required('admin')
def admin_report():
 from sqlalchemy import func
 apps=Application.query.count(); customers=User.query.filter_by(role='customer').count()
 loan_count=Loan.query.count()
 principal=db.session.query(func.coalesce(func.sum(Loan.principal),0)).scalar()
 pending=Application.query.filter_by(kyc_status='pending').count()
 successful=Payment.query.filter_by(status='success').count()
 return render_template('report.html',apps=apps,customers=customers,loan_count=loan_count,principal=principal,pending=pending,successful=successful)

@app.get('/admin/report.csv')
@login_required('admin')
def admin_report_csv():
 import csv, io
 from flask import Response
 stream=io.StringIO(); writer=csv.writer(stream)
 writer.writerow(['loan_id','application_id','principal_inr','rate_percent','rate_period','method','tenure_months','status','total_repayment_inr'])
 for l in Loan.query.order_by(Loan.id).all():
  writer.writerow([l.id,l.application_id,str(l.principal),str(l.rate),l.annual_or_monthly,l.method,l.tenure,l.status,str(l.total)])
 audit('admin_export_loans','report:csv'); db.session.commit()
 return Response(stream.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=owl-finance-loans.csv','Cache-Control':'no-store'})

def initialize_database_and_admin():
    # Runs on Gunicorn startup as well as local startup.
    with app.app_context():
        db.create_all()
        email = os.getenv('ADMIN_EMAIL', '').strip().lower()
        password = os.getenv('ADMIN_PASSWORD', '')

        if not email or not password:
            app.logger.warning('Admin bootstrap skipped: ADMIN_EMAIL or ADMIN_PASSWORD is missing.')
            return
        if len(password) < 12:
            app.logger.error('Admin bootstrap skipped: ADMIN_PASSWORD must contain at least 12 characters. Change it in Render Environment and redeploy.')
            return

        existing = User.query.filter_by(email=email).first()
        if existing:
            if existing.role != 'admin':
                app.logger.error('Admin bootstrap blocked: ADMIN_EMAIL belongs to an existing non-admin user. No role was changed.')
            else:
                app.logger.info('Admin account already exists; password was not changed.')
            return

        try:
            db.session.add(User(
                name='OWL FINANCE Admin',
                email=email,
                password=generate_password_hash(password),
                role='admin'
            ))
            db.session.commit()
            app.logger.info('Initial OWL FINANCE administrator created successfully.')
        except Exception:
            db.session.rollback()
            # Two Gunicorn workers may try to create the same account simultaneously.
            if User.query.filter_by(email=email, role='admin').first():
                app.logger.info('Administrator was initialized by another worker.')
            else:
                app.logger.exception('Admin bootstrap failed.')
                raise

initialize_database_and_admin()

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG') == '1')
