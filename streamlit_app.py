import streamlit as st
import ee

# 1. Sahifa sarlavhasi
st.set_page_config(page_title="Shovot Monitoring", layout="wide")
st.title("🛰 Shovot tumani Onlayn Monitoring Tizimi")

# 2. GEE ni ishga tushirish (Loyihani aniq ko'rsatgan holda)
def gee_init():
    try:
        gee_key = st.secrets["gee_key"]
        credentials = ee.ServiceAccountCredentials(
            gee_key['client_email'],
            key_data=gee_key['private_key']
        )
        # BU YERDA: project_id ni aniq ko'rsatish xatolikni oldini oladi
        ee.Initialize(credentials, project=gee_key['project_id'])
        return True
    except Exception as e:
        st.error(f"GEE ulanishida xatolik: {e}")
        return False

if gee_init():
    st.sidebar.success("✅ GEE bilan aloqa o'rnatildi!")
    yil = st.sidebar.slider("Yilni tanlang", 2015, 2024, 2023)
    
    # 3. Hududni topish (Shavat deb yozish ishonchliroq)
    region = ee.FeatureCollection('FAO/GAUL/2015/level2') \
               .filter(ee.Filter.eq('ADM2_NAME', 'Shavat'))

    # 4. NDVI hisoblash
    dataset = ee.ImageCollection('MODIS/006/MOD13A2') \
                .filterDate(f'{yil}-05-01', f'{yil}-08-31') \
                .select('NDVI') \
                .median() \
                .clip(region)

    # 5. Xatolikdan himoyalangan holda ma'lumotni olish
    try:
        info = dataset.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region.geometry(),
            scale=1000
        ).get('NDVI').getInfo()

        if info:
            ndvi_final = round(info * 0.0001, 3)
            st.metric(label=f"{yil}-yil yozgi o'rtacha NDVI", value=ndvi_final)
            if ndvi_final < 0.25:
                st.error("📉 Holat: O'simlik qoplami kam.")
            else:
                st.success("🌿 Holat: Yashillik darajasi yaxshi.")
        else:
            st.warning("Ushbu yil uchun ma'lumot hisoblab bo'lmadi. Boshqa yilni tanlab ko'ring.")
    except Exception as e:
        st.error("Ma'lumotni yuklashda xatolik yuz berdi. Google Cloud-da Earth Engine API yoqilganligini tekshiring.")
