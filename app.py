import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import json

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="TSI Yönetim Paneli", layout="wide", page_icon="🚀")

# --- MODERN UI CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    div[data-testid="metric-container"] {
        background-color: #ffffff; border: 1px solid #e0e0e0; padding: 5% 10%;
        border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    div.stButton > button { border-radius: 8px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 1. GOOGLE SHEETS BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def veriyi_yukle():
    try:
        # Önbelleği kapatıyoruz (ttl=0) ki her zaman güncel veri gelsin
        df = conn.read(ttl=0)
        # Tarih sütununu düzelt
        if 'BAŞLANGIÇ' in df.columns:
            df['BAŞLANGIÇ'] = pd.to_datetime(df['BAŞLANGIÇ']).dt.strftime('%Y-%m-%d')
        return df
    except Exception as e:
        st.error(f"Veri yüklenirken hata oluştu: {e}")
        columns = ['GÖREV ADI', 'FİRMA', 'ANA SORUMLU', 'BAŞLANGIÇ', 'BİTİŞ', 'DURUM', 'ÖNCELİK', 'NOTLAR', 'AŞAMALAR', 'KAYIT_TARIHI']
        return pd.DataFrame(columns=columns)

def veriyi_kaydet(df):
    conn.update(data=df)

# Yardımcı Fonksiyonlar
def asamalari_coz(asama_metni):
    try:
        if pd.isna(asama_metni) or asama_metni == "": return []
        if isinstance(asama_metni, list): return asama_metni
        asamalar = json.loads(str(asama_metni))
        return asamalar if isinstance(asamalar, list) else []
    except:
        return []

def asamalari_paketle(asama_listesi):
    return json.dumps(asama_listesi, ensure_ascii=False)

# --- VERİYİ ÇEK ---
if 'data' not in st.session_state:
    st.session_state.data = veriyi_yukle()

# --- KULLANICI LİSTESİ ---
kullanicilar = ["Yönetici", "Zilan Demir", "Nilay", "Saim", "Uğur"]
sorumlular = [k for k in kullanicilar if k != "Yönetici"]

# --- SIDEBAR FİLTRELER ---
st.sidebar.title("🚀 TSI İş Takip")
firmalar = sorted(st.session_state.data['FİRMA'].unique().tolist()) if not st.session_state.data.empty else ["Genel"]

f_firma = st.sidebar.multiselect("Firma Filtresi", firmalar)
f_durum = st.sidebar.multiselect("Durum Filtresi", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"])

display_df = st.session_state.data.copy()
if f_firma: display_df = display_df[display_df['FİRMA'].isin(f_firma)]
if f_durum: display_df = display_df[display_df['DURUM'].isin(f_durum)]

# --- ANA SEKMELER ---
tab_liste, tab_ekle, tab_rapor = st.tabs(["📋 İş Listesi ve Detaylar", "➕ Yeni Görev", "📊 Raporlama"])

# ================= TAB 1: LİSTE VE TIKLA-DÜZENLE PANELİ =================
with tab_liste:
    st.subheader("📋 Ana Görevler")
    
    if not display_df.empty:
        gosterilecek_df = display_df.drop(columns=['AŞAMALAR', 'KAYIT_TARIHI'], errors='ignore')
        
        selection = st.dataframe(
            gosterilecek_df,
            use_container_width=True,
            height=350,
            selection_mode="single_row",
            on_select="rerun",
            key="main_table"
        )

        selected_rows = selection.get("selection", {}).get("rows", [])
        
        if selected_rows:
            idx = gosterilecek_df.index[selected_rows[0]]
            secili_satir = st.session_state.data.loc[idx]
            
            st.divider()
            with st.container(border=True):
                st.markdown(f"### 🎯 Detay: {secili_satir['GÖREV ADI']}")
                
                col1, col2 = st.columns(2)
                yeni_durum = col1.selectbox("Genel Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"], 
                                          index=["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"].index(secili_satir['DURUM']) if secili_satir['DURUM'] in ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"] else 0)
                yeni_not = col2.text_input("Genel Not", value=str(secili_satir['NOTLAR']) if pd.notna(secili_satir['NOTLAR']) else "")

                st.write("#### 🛠 Alt Aşamalar")
                mevcut_asamalar = asamalari_coz(secili_satir['AŞAMALAR'])
                asama_df = pd.DataFrame(mevcut_asamalar) if mevcut_asamalar else pd.DataFrame(columns=["Aşama Adı", "Sorumlu", "Durum", "Not"])
                
                duzenlenen_asamalar = st.data_editor(
                    asama_df, 
                    num_rows="dynamic", 
                    use_container_width=True,
                    column_config={
                        "Sorumlu": st.column_config.SelectboxColumn(options=sorumlular),
                        "Durum": st.column_config.SelectboxColumn(options=["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal"])
                    },
                    key=f"editor_{idx}"
                )

                if st.button("💾 Google Sheets'e Kaydet", use_container_width=True):
                    st.session_state.data.at[idx, 'DURUM'] = yeni_durum
                    st.session_state.data.at[idx, 'NOTLAR'] = yeni_not
                    st.session_state.data.at[idx, 'AŞAMALAR'] = asamalari_paketle(duzenlenen_asamalar.to_dict('records'))
                    
                    veriyi_kaydet(st.session_state.data)
                    st.success("Kaydedildi! Sayfa yenileniyor...")
                    st.rerun()
        else:
            st.info("💡 Detayları görmek için listeden bir işe tıklayın.")
    else:
        st.warning("Henüz hiç görev yok veya filtreleriniz hiçbir sonuç vermedi.")

# ================= TAB 2: YENİ GÖREV EKLEME =================
with tab_ekle:
    with st.form("yeni_is_formu", clear_on_submit=True):
        c1, c2 = st.columns(2)
        v_ad = c1.text_input("Görev Adı *")
        v_firma = c1.text_input("Firma *")
        
        v_sorumlu = c2.selectbox("Ana Sorumlu *", sorumlular)
        v_bitis = c2.date_input("Hedef Bitiş", datetime.now() + timedelta(days=7))
        
        v_oncelik = st.selectbox("Öncelik", ["Düşük", "Orta", "Yüksek"])
        v_not = st.text_area("Notlar")
        
        submit = st.form_submit_button("✅ GÖREVİ OLUŞTUR")
        
        if submit and v_ad and v_firma:
            yeni = {
                'GÖREV ADI': v_ad, 'FİRMA': v_firma, 'ANA SORUMLU': v_sorumlu,
                'BAŞLANGIÇ': datetime.now().strftime('%Y-%m-%d'), 'BİTİŞ': v_
