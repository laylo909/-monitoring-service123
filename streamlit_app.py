import streamlit as st
import ee
import json

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
        # 1. Secrets'dan ma'lumotlarni olish
        project_id = st.secrets.get("GEE_PROJECT_ID") or st.secrets.get("gee_key", {}).get("project_id")
        client_email = st.secrets.get("GEE_SERVICE_ACCOUNT") or st.secrets.get("gee_key", {}).get("client_email")
        private_key = st.secrets.get("GEE_PRIVATE_KEY") or st.secrets.get("gee_key", {}).get("private_key")
        
        # 2. Tekshirish
        if not all([project_id, client_email, private_key]):
            missing = []
            if not project_id: missing.append("project_id")
            if not client_email: missing.append("client_email")
            if not private_key: missing.append("private_key")
            return False, f"Secrets yetishmayapti: {', '.join(missing)}"
        
        # 3. Credentials yaratish
        credentials = ee.ServiceAccountCredentials(
            client_email,
            key_data=private_key
        )
        
        # 4. Initialize
        ee.Initialize(credentials, project=project_id)
        return True, project_id
        
    except Exception as e:
        return False, str(e)

# ========== GEE ULANGANLIGINI TEKSHIRISH ==========
is_connected, msg = init_gee()

if not is_connected:
    st.error(f"❌ GEE ulanishida xatolik: {msg}")
    st.info("""
    **Tekshirish ro'yxati:**
    1. Streamlit Cloud → Settings → Secrets bo'limida quyidagilar borligini tekshiring:
       - `GEE_PROJECT_ID`
       - `GEE_SERVICE_ACCOUNT` 
       - `GEE_PRIVATE_KEY`
    2. Google Cloud'da Earth Engine API yoqilganligini tekshiring
    3. Service Account'ga `Earth Engine Resource Viewer` roli berilganligini tekshiring
    """)
    st.stop()  # Ilovani to'xtatish

st.sidebar.success(f"✅ GEE ulanish: {msg}")

# ========== YIL TANLASH ==========
yil = st.sidebar.slider("📅 Yilni tanlang", 2015, 2024, 2023)

# ========== HUDUDNI TOPISH (DEBUG bilan) ==========
@st.cache_data(ttl=3600)
def get_region():
    """Shovot hududini GEE'dan olish"""
    try:
        # Bir nechta variant bilan qidirish
        region = ee.FeatureCollection('FAO/GAUL/2015/level2') \
                   .filter(ee.Filter.Or(
                       ee.Filter.eq('ADM2_NAME', 'Shavat'),
                       ee.Filter.eq('ADM2_NAME', 'Shovot'),
                       ee.Filter.eq('ADM2_NAME', 'Shovot tumani')
                   ))
        
        # Tekshirish
        count = region.size().getInfo()
        if count == 0:
            return None, "Shovot/Shavat hududi topilmadi"
        
        return region, f"Hudud topildi ({count} ta obyekt)"
        
    except Exception as e:
        return None, str(e)

region, region_msg = get_region()

if region is None:
    st.error(f"❌ Hudud topilmadi: {region_msg}")
    st.info("FAO/GAUL ma'lumotlar bazasida 'Shovot' yoki 'Shavat' nomi yo'q. Boshqa nom bilan qidirish kerak.")
    st.stop()

st.sidebar.info(f"🗺️ {region_msg}")

# ========== NDVI HISOBLASH (KESH bilan) ==========
@st.cache_data(ttl=1800)
def calculate_ndvi(year):
    """NDVI ni hisoblash"""
    try:
        # 1. Ma'lumotlar to'plamini olish
        dataset = ee.ImageCollection('MODIS/006/MOD13A2') \
                    .filterDate(f'{year}-05-01', f'{year}-08-31') \
                    .select('NDVI') \
                    .median() \
                    .clip(region)
        
        # 2. Tekshirish - rasm borligini
        image_info = dataset.getInfo()
        if image_info is None:
            return None, f"{year}-yil uchun MODIS ma'lumoti yo'q"
        
        # 3. ReduceRegion bilan hisoblash
        stats = dataset.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region.geometry(),
            scale=1000,
            maxPixels=1e9,
            bestEffort=True
        )
        
        ndvi_raw = stats.get('NDVI').getInfo()
        
        if ndvi_raw is None:
            return None, "NDVI qiymati hisoblab bo'lmadi (bulut/qor yoki ma'lumot yo'q)"
        
        ndvi_final = round(ndvi_raw * 0.0001, 3)
        return ndvi_final, "OK"
        
    except ee.EEException as e:
        # GEE xatoliklari
        error_msg = str(e)
        if "Earth Engine API" in error_msg:
            return None, "Earth Engine API yoqilmagan yoki ruxsat yo'q"
        elif "computation timed out" in error_msg:
            return None, "Hisoblash vaqti tugadi (katta hudud yoki murakkab so'rov)"
        else:
            return None, f"GEE xatosi: {error_msg}"
            
    except Exception as e:
        return None, f"Tizim xatosi: {str(e)}"

# ========== NATIJANI KO'RSATISH ==========
with st.spinner(f"⏳ {yil}-yil ma'lumoti yuklanmoqda..."):
    ndvi_value, status = calculate_ndvi(yil)

if ndvi_value is None:
    st.error(f"❌ {status}")
    
    # Qo'shimcha yordam
    if "API" in status:
        st.warning("🔧 [Google Cloud Console](https://console.cloud.google.com/) ga kiring → APIs & Services → Earth Engine API → Enable")
    elif "timed out" in status:
        st.info("💡 Kichikroq hudud yoki boshqa yilni tanlab ko'ring")
    elif "ma'lumoti yo'q" in status:
        st.info("💡 Boshqa yilni tanlang (2015-2024)")
        
else:
    # Natijani ko'rsatish
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label=f"📊 {yil}-yil yozgi o'rtacha NDVI",
            value=f"{ndvi_value}"
        )
    
    with col2:
        if ndvi_value < 0.1:
            st.error("🏜️ **Holat:** O'simlik qoplami juda kam (cho'l/kurak)")
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
    
    # Vizual tahlil
    st.divider()
    st.subheader("📈 NDVI Tahlili")
    
    if ndvi_value < 0.2:
        st.write("""
        **Sabablar:**
        - Suv yetishmovchiligi
        - Tuzlanish
        - Ekinzorlarni sugorish tartibini tekshiring
        """)
    elif ndvi_value > 0.5:
        st.write("""
        **Xulosa:**
        - Vegetatsiya holati yaxshi
        - Sug'orish tizimi to'g'ri ishlayapti
        """)
