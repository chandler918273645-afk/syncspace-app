from flask import Flask, request, jsonify, render_template, session
from supabase import create_client, Client
from datetime import datetime, timedelta
import os

app = Flask(__name__, template_folder='.')
app.secret_key = 'super_gizli_anahtar'
app.permanent_session_lifetime = timedelta(days=30)

# SUPABASE BAĞLANTI AYARLARI
# NOT: Buradaki bilgileri kendi Supabase panelinden aldıklarınla değiştir!
SUPABASE_URL = "https://fdwuwfoduutfvgqxektw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZkd3V3Zm9kdXV0ZnZncXhla3R3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg3ODA1NTgsImV4cCI6MjA5NDM1NjU1OH0.HWps6z_lFwst5peNT2QjMHsaUHGNDFSopJKoiRcrbe8"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/oturum_kontrol', methods=['GET'])
def oturum_kontrol():
    if 'kullanici' in session:
        return jsonify({"durum": "ok", "kullanici": session['kullanici']})
    return jsonify({"durum": "yok"})

@app.route('/cikis_yap', methods=['POST'])
def cikis_yap():
    session.pop('kullanici', None)
    return jsonify({"mesaj": "Çıkış yapıldı!"})

@app.route('/kayit_veya_giris', methods=['POST'])
def kayit_veya_giris():
    data = request.json
    k_adi = data['kullanici_adi']
    sifre = data['sifre']
    beni_hatirla = data.get('beni_hatirla', False)
    
    # Kullanıcıyı buluttan çek
    res = supabase.table('kullanicilar').select('*').eq('kullanici_adi', k_adi).execute()
    user = res.data
    
    if len(user) > 0:
        if user[0]['sifre'] == sifre:
            session['kullanici'] = k_adi
            if beni_hatirla: session.permanent = True
            return jsonify({"mesaj": "Giriş başarılı!", "durum": "ok"})
        else:
            return jsonify({"mesaj": "Hatalı şifre!", "durum": "hata"})
    else:
        # Yeni kullanıcıyı buluta kaydet
        supabase.table('kullanicilar').insert({'kullanici_adi': k_adi, 'sifre': sifre}).execute()
        session['kullanici'] = k_adi
        if beni_hatirla: session.permanent = True
        return jsonify({"mesaj": "Yeni kayıt oluşturuldu ve giriş yapıldı!", "durum": "ok"})

# --- ARKADAŞLIK SİSTEMİ ---
@app.route('/istek_gonder', methods=['POST'])
def istek_gonder():
    if 'kullanici' not in session: return jsonify({"mesaj": "Önce giriş yapın"})
    hedef = request.json['arkadas_adi']
    ben = session['kullanici']
    if hedef == ben: return jsonify({"mesaj": "Kendine istek atamazsın!"})
        
    kisi_res = supabase.table('kullanicilar').select('*').eq('kullanici_adi', hedef).execute()
    if len(kisi_res.data) == 0: return jsonify({"mesaj": "Böyle bir kullanıcı bulunamadı!"})
        
    ark_res = supabase.table('arkadaslar').select('*').eq('kullanici1', ben).eq('kullanici2', hedef).execute()
    if len(ark_res.data) > 0: return jsonify({"mesaj": "Bu kişiyle zaten arkadaşsın!"})
        
    istek1 = supabase.table('istekler').select('*').eq('gonderen', ben).eq('alan', hedef).execute()
    if len(istek1.data) > 0: return jsonify({"mesaj": "Zaten istek gönderdin!"})
        
    istek2 = supabase.table('istekler').select('*').eq('gonderen', hedef).eq('alan', ben).execute()
    if len(istek2.data) > 0: return jsonify({"mesaj": f"{hedef} sana zaten istek göndermiş!"})
        
    supabase.table('istekler').insert({'gonderen': ben, 'alan': hedef}).execute()
    return jsonify({"mesaj": "İstek gönderildi!"})

@app.route('/istekleri_getir', methods=['GET'])
def istekleri_getir():
    if 'kullanici' not in session: return jsonify({"istekler": []})
    res = supabase.table('istekler').select('gonderen').eq('alan', session['kullanici']).execute()
    istekler = [r['gonderen'] for r in res.data]
    return jsonify({"istekler": istekler})

@app.route('/istek_cevapla', methods=['POST'])
def istek_cevapla():
    if 'kullanici' not in session: return jsonify({"mesaj": "Önce giriş yapın"})
    ben = session['kullanici']
    gonderen = request.json['gonderen']
    islem = request.json['islem']
    
    res = supabase.table('istekler').select('*').eq('gonderen', gonderen).eq('alan', ben).execute()
    if len(res.data) > 0:
        supabase.table('istekler').delete().eq('gonderen', gonderen).eq('alan', ben).execute()
        if islem == 'kabul':
            supabase.table('arkadaslar').insert([
                {'kullanici1': ben, 'kullanici2': gonderen},
                {'kullanici1': gonderen, 'kullanici2': ben}
            ]).execute()
            mesaj = f"{gonderen} ile arkadaş oldunuz!"
        else:
            mesaj = "İstek reddedildi."
    else:
        mesaj = "İstek bulunamadı."
    return jsonify({"mesaj": mesaj})

@app.route('/arkadas_sil', methods=['POST'])
def arkadas_sil():
    if 'kullanici' not in session: return jsonify({"mesaj": "Önce giriş yapın"})
    arkadas = request.json['arkadas_adi']
    ben = session['kullanici']
    supabase.table('arkadaslar').delete().eq('kullanici1', ben).eq('kullanici2', arkadas).execute()
    supabase.table('arkadaslar').delete().eq('kullanici1', arkadas).eq('kullanici2', ben).execute()
    return jsonify({"mesaj": "Bağlantı kesildi."})

@app.route('/arkadaslari_getir', methods=['GET'])
def arkadaslari_getir():
    if 'kullanici' not in session: return jsonify({"arkadaslar": []})
    res = supabase.table('arkadaslar').select('kullanici2').eq('kullanici1', session['kullanici']).execute()
    arkadaslar = [r['kullanici2'] for r in res.data]
    return jsonify({"arkadaslar": arkadaslar})

# --- TAKVİM SİSTEMİ ---
@app.route('/plan_ekle', methods=['POST'])
def plan_ekle():
    if 'kullanici' not in session: return jsonify({"mesaj": "Önce giriş yapın"})
    data = request.json
    supabase.table('planlar').insert({
        'kullanici_adi': session['kullanici'], 
        'isim': data['isim'], 
        'tarih': data['tarih'], 
        'baslangic': data['baslangic'], 
        'bitis': data['bitis']
    }).execute()
    return jsonify({"mesaj": "Plan eklendi!"})

@app.route('/takvim_getir', methods=['GET'])
def takvim_getir():
    if 'kullanici' not in session: return jsonify({"mesaj": "Önce giriş yapın"})
    res = supabase.table('planlar').select('tarih, baslangic, bitis, isim').eq('kullanici_adi', session['kullanici']).order('tarih').execute()
    return jsonify({"planlar": res.data})

def turkce_tarih_formatla(tarih_str):
    aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    t = datetime.strptime(tarih_str, '%Y-%m-%d')
    return f"{t.day} {aylar[t.month - 1]} {gunler[t.weekday()]}"

@app.route('/ortak_saat_bul', methods=['POST'])
def ortak_saat_bul():
    if 'kullanici' not in session: return jsonify({"mesaj": "Önce giriş yapın"})
    data = request.json
    arkadas_listesi = data.get('arkadas_listesi', [])
    
    if not arkadas_listesi:
        return jsonify({"mesaj": "Lütfen en az bir kişi seçin!", "sonuclar": []})

    gun_tipi = data['gun_tipi']
    zaman_dilimi = data['zaman_dilimi']
    hedef_tarih = data.get('tarih', '')
    
    ben = session['kullanici']
    katilimcilar = [ben] + arkadas_listesi

    kontrol_edilecek_gunler = []
    bugun = datetime.today()

    if gun_tipi == 'belirli_gun' and hedef_tarih:
        kontrol_edilecek_gunler.append(hedef_tarih)
    else:
        for i in range(30):
            test_gunu = bugun + timedelta(days=i)
            haftanin_gunu = test_gunu.weekday()
            tarih_str = test_gunu.strftime('%Y-%m-%d')
            if gun_tipi == 'hafta_ici' and haftanin_gunu < 5: kontrol_edilecek_gunler.append(tarih_str)
            elif gun_tipi == 'hafta_sonu' and haftanin_gunu >= 5: kontrol_edilecek_gunler.append(tarih_str)
            elif gun_tipi == 'herhangi': kontrol_edilecek_gunler.append(tarih_str)

    bas_saat, bit_saat = 9, 23
    if zaman_dilimi == 'sabah': bit_saat = 12
    elif zaman_dilimi == 'oglen': bas_saat, bit_saat = 12, 18
    elif zaman_dilimi == 'aksam': bas_saat = 18
    elif zaman_dilimi == 'ozel':
        bas_saat = int(data.get('ozel_bas', '09:00').split(':')[0])
        bit_saat = int(data.get('ozel_bit', '23:00').split(':')[0])

    tum_sonuclar = []

    for gun in kontrol_edilecek_gunler:
        if len(tum_sonuclar) >= 3: break
        
        # Çoklu katılımcı için bulut sorgusu
        res = supabase.table('planlar').select('baslangic, bitis').eq('tarih', gun).in_('kullanici_adi', katilimcilar).execute()
        dolu_saatler = [(r['baslangic'], r['bitis']) for r in res.data]
        
        tum_saatler = [f"{str(saat).zfill(2)}:00" for saat in range(bas_saat, bit_saat)]
        musait_saatler = []
        for saat in tum_saatler:
            saat_obj = datetime.strptime(saat, '%H:%M')
            cakisma = any(datetime.strptime(bas, '%H:%M') <= saat_obj < datetime.strptime(bit, '%H:%M') for bas, bit in dolu_saatler)
            if not cakisma: musait_saatler.append(saat)
        
        if musait_saatler:
            araliklar = []
            gecici_bas = musait_saatler[0]
            onceki_saat_int = int(gecici_bas.split(':')[0])
            for saat in musait_saatler[1:]:
                su_anki_saat_int = int(saat.split(':')[0])
                if su_anki_saat_int == onceki_saat_int + 1: onceki_saat_int = su_anki_saat_int
                else:
                    araliklar.append(f"{gecici_bas}-{str(onceki_saat_int + 1).zfill(2)}:00")
                    gecici_bas = saat; onceki_saat_int = su_anki_saat_int
            araliklar.append(f"{gecici_bas}-{str(onceki_saat_int + 1).zfill(2)}:00")
            saat_metni = ", ".join(araliklar)
            if saat_metni == "09:00-23:00": saat_metni = "Tüm Gün"
            tum_sonuclar.append({"tarih": turkce_tarih_formatla(gun), "saatler": saat_metni})

    return jsonify({"sonuclar": tum_sonuclar})

if __name__ == '__main__':
    # Flask sunucusunu başlat
    app.run(debug=True, port=5000)