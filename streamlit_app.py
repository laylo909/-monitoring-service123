import streamlit as st
import ee
import pandas as pd

# 1. Google Earth Engine-ni kalit orqali ishga tushirish
def sarlavha_sozlamalari():
    st.set_page_config(page_title="Shavat Monitoring", layout="wide")
    st.title("🛰 Shavat tumani Onlayn Monitoring Tizimi")
    st.write("Google Earth Engine va Streamlit yordamida NDVI tahlili")

def gee_init():
    try:
        # Streamlit Secrets-dan kalitni olish
        gee_key = st.secrets["gee_key"]
        
        # Avtorizatsiya
        credentials = ee.ServiceAccountCredentials(
            gee_key['client_email'],
            key_data=gee_key['private_key']
        )
        ee.Initialize(credentials)
        return True
    except Exception as e:
        st.error(f"GEE ulanishida xatolik: {e}")
        return False

# 2. Asosiy dastur mantiqi
if gee_init():
    st.sidebar.success("GEE bilan aloqa o'rnatildi!")
    
    # Yilni tanlash
    yil = st.sidebar.slider("Yilni tanlang", 2015, 2024, 2023)
    
    # Hududni belgilash (Shovot tumani)
    # Eslatma: 'ADM2_NAME' nomi GEE bazasida 'Shavat' deb yozilgan bo'lishi mumkin
    region = ee.FeatureCollection('FAO/GAUL/2015/level2') \
               .filter(ee.Filter.eq('ADM2_NAME', 'Shavat')) # yoki 'Shavat'
    
    # Ma'lumotlarni yuklash (MODIS NDVI)
    start_date = f'{yil}-05-01'
    end_date = f'{yil}-08-31'
    
    dataset = ee.ImageCollection('MODIS/006/MOD13A2') \
                .filterDate(start_date, end_date) \
                .select('NDVI') \
                .median() \
                .clip(region)

    # NDVI qiymatini hisoblash (O'rtacha)
    mean_ndvi = dataset.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region.geometry(),
        scale=1000
    ).get('NDVI').getInfo()

    # Natijalarni ko'rsatish
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(label=f"{yil}-yil uchun O'rtacha NDVI", value=round(mean_ndvi * 0.0001, 3))
        st.info("NDVI ko'rsatkichi 0.2 dan yuqori bo'lsa - o'simliklar holati yaxshi hisoblanadi.")

    with col2:
        if (mean_ndvi * 0.0001) < 0.25:
            st.warning("⚠️ Diqqat: Ushbu yilda o'simlik qoplami past bo'lgan (Qurg'oqchilik xavfi).")
        else:
            st.success("✅ Holat barqaror: Yashillik darajasi me'yorda.")

else:
    st.warning("Iltimos, Secrets bo'limiga kalitlarni to'g'ri joylang.")
