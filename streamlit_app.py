import streamlit as st
import ee

# ========== SAHIFA SOZLAMALARI ==========
st.set_page_config(
    page_title="Shovot Monitoring",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🛰️ Shovot tumani Onlayn Monitoring Tizimi")

# ========== GEE ULANISHI ==========
@st.cache_resource
def init_gee():
    """GEE bilan ulanishni bir marta sozlash"""
    try:
        project_id = st.secrets.get("GEE_PROJECT_ID")
        client_email = st.secrets.get("GEE_SERVICE_ACCOUNT")
        private_key = st.secrets.get("GEE_PRIVATE_KEY")
        
        if not all([project_id, client_email, private_key]):
            missing = []
            if not project_id: missing.append("GEE_PROJECT_ID")
            if not client_email: missing.append("GEE_SERVICE_ACCOUNT")
            if not private_key: missing.append("GEE_PRIVATE_KEY")
            return False, f"Secrets yetishmayapti: {', '.join(missing)}"
        
        credentials = ee.ServiceAccountCredentials(
            client_email,
            key_data=private_key
        )
        ee.Initialize(credentials, project=project_id)
        return True, project_id
        
    except Exception as e:
        return False, str(e)

# ========== GEE ULANGANLIGINI TEKSHIRISH ==========
is_connected, msg = init_gee()

if not is_connected:
    st.error(f"❌ GEE ulanishida xatolik: {msg}")
    st.stop()

st.sidebar.success(f"✅ GEE ulanish: {msg}")

# ========== YIL TANLASH ==========
yil = st.sidebar.slider("📅 Yilni tanlang", 2015, 2024, 2023)

# ========== HUDUDNI TOPISH ==========
@st.cache_data(ttl=3600)
def get_region():
    """Shovot hududini GEE'dan olish"""
    try:
        region = ee.FeatureCollection('FAO/GAUL/2015/level2') \
                   .filter(ee.Filter.Or(
                       ee.Filter.eq('ADM2_NAME', 'Shavat'),
                       ee.Filter.eq('ADM2_NAME', 'Shovot'),
                       ee.Filter.eq('ADM2_NAME', 'Shovot tumani')
                   ))
        
        count = region.size().getInfo()
        if count == 0:
            return None, "Shovot/Shavat hududi topilmadi"
        
        return region, f"Hudud topildi ({count} ta obyekt)"
        
    except Exception as e:
        return None, str(e)

region, region_msg = get_region()

if region is None:
    st.error(f"❌ Hudud topilmadi: {region_msg}")
    st.stop()

st.sidebar.info(f"🗺️ {region_msg}")

# ========== BU YERDA XATO BO'LGAN - TO'G'RILANDI ==========
# ❌ XATO:    def generate_ndvi_data(district, date_start, date_end):
# ✅ TO'G'RI: def generate_ndvi_data(district, date_start, date_end):

def generate_ndvi_data(district, date_start, date_end):
    """NDVI ma'lumotlarini yaratish"""
    try:
        # Hududni filtrlash
        region = ee.FeatureCollection('FAO/GAUL/2015/level2') \
                   .filter(ee.Filter.eq('ADM2_NAME', district))
        
        # MODIS NDVI
        dataset = ee.ImageCollection('MODIS/006/MOD13A2') \
                    .filterDate(date_start, date_end) \
                    .select('NDVI') \
                    .median() \
                    .clip(region)
        
        # Hisoblash
        stats = dataset.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region.geometry(),
            scale=1000,
            maxPixels=1e9,
            bestEffort=True
        )
        
        ndvi_raw = stats.get('NDVI').getInfo()
        
        if ndvi_raw is None:
            return None, "NDVI qiymati hisoblab bo'lmadi"
        
        ndvi_final = round(ndvi_raw * 0.0001, 3)
        return ndvi_final, "OK"
        
    except Exception as e:
        return None, str(e)

# ========== NDVI HISOBLASH ==========
@st.cache_data(ttl=1800)
def calculate_ndvi(year):
    """Asosiy NDVI hisoblash funksiyasi"""
    date_start = f'{year}-05-01'
    date_end = f'{year}-08-31'
    
    ndvi_value, status = generate_ndvi_data('Shavat', date_start, date_end)
    return ndvi_value, status

# ========== NATIJANI KO'RSATISH ==========
with st.spinner(f"⏳ {yil}-yil ma'lumoti yuklanmoqda..."):
    ndvi_value, status = calculate_ndvi(yil)

if ndvi_value is None:
    st.error(f"❌ {status}")
else:
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label=f"📊 {yil}-yil yozgi o'rtacha NDVI",
            value=f"{ndvi_value}"
        )
    
    with col2:
        if ndvi_value < 0.1:
            st.error("🏜️ **Holat:** O'simlik qoplami juda kam")
            st.progress(0.1)
        elif ndvi_value < 0.25:
            st.warning("📉 **Holat:** O'simlik qoplami past")
            st.progress(0.3)
        elif ndvi_value < 0.4:
            st.info("🌱 **Holat:** O'rtacha yashillik")
            st.progress(0.5)
        elif ndvi_value < 0.6:
            st.success("🌿 **Holat:** Yaxshi yashillik")
            st.progress(0.7)
        else:
            st.success("🌳 **Holat:** A'lo yashillik!")
            st.progress(1.0)
