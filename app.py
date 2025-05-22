# app.py: Streamlit dashboard con ottimizzazione avanzata e filtri dinamici per utente

import streamlit as st
import pandas as pd

# -------------------------------------------
# Configurazione pagina
# -------------------------------------------
st.set_page_config(page_title="Dashboard Prodotti & Applicazioni", layout="wide")
st.markdown(
    """
    <style>
      .main > .block-container { padding:1rem 2rem; }
      h1 { font-size:2.5rem; color:#334155; margin-bottom:0.5rem; }
      .sidebar .sidebar-content { background-color:#F1F5F9; padding:1rem; border-radius:8px; }
      .stButton>button { background-color:#2563EB; color:white; border-radius:6px; }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------
# Sidebar: upload file
# -------------------------------------------
with st.sidebar:
    st.markdown("## 📥 Carica i file Excel")
    prod_file = st.file_uploader("Dati Prodotti", type=["xlsx","xls"])
    ref_file  = st.file_uploader("Riferimenti Originali", type=["xlsx","xls"])
    app_file  = st.file_uploader("Applicazioni Macchine", type=["xlsx","xls"])

missing = not (prod_file and ref_file and app_file)
if missing:
    st.sidebar.warning("Carica tutti e tre i file per procedere.")

# -------------------------------------------
# Funzioni di caching
# -------------------------------------------
@st.cache_data
def load_df(uploaded_file):
    uploaded_file.seek(0)
    try:
        return pd.read_excel(uploaded_file, dtype=str)
    except Exception as err:
        st.error(f"Errore lettura {uploaded_file.name}: {err}")
        st.stop()

@st.cache_data
def preprocess():
    df_prod = load_df(prod_file)
    df_ref  = load_df(ref_file)
    df_app  = load_df(app_file)

    # pivot riferimenti
    temp = df_ref.copy()
    temp['idx'] = temp.groupby('code').cumcount() + 1
    piv = temp.pivot(index='code', columns='idx', values=['company_name','relation_code'])
    piv.columns = [f"brand{i}" if c=='company_name' else f"reference{i}" for c,i in piv.columns]
    piv = piv.reset_index().rename(columns={'code':'sku'})
    piv['sku_stripped'] = piv['sku'].str.lstrip('0')

    # merge prodotti
    if 'product_code' in df_prod.columns:
        df_prod['prod_stripped'] = df_prod['product_code'].str.lstrip('0')
    merged = df_prod.merge(piv, left_on='prod_stripped', right_on='sku_stripped', how='left')

    # mappa colonne per category_text
    col_map = {}
    if 'category_text' in merged.columns:
        for cat in merged['category_text'].dropna().unique():
            sub = merged[merged['category_text']==cat]
            col_map[cat] = [c for c in sub.columns if sub[c].notna().any()]

    # preparazione applicazioni
    df_app['relation_code'] = df_app['relation_code'].fillna('')
    long = df_app.assign(reference_app=df_app['relation_code'].str.split(','))
    long = long.explode('reference_app')
    long['reference_app'] = long['reference_app'].str.strip()
    long = long[long['reference_app']!='']
    long = long.rename(columns={'company_name':'brand_app','code':'sku'})[['sku','brand_app','reference_app']]

    return merged, df_ref, long, col_map

# -------------------------------------------
# Rendering UI se i file ci sono
# -------------------------------------------
if not missing:
    df_prod, df_ref_orig, df_apps, col_map = preprocess()
    t1, t2, t3 = st.tabs(["Prodotti","Riferimenti","Applicazioni"])

    # Tab Prodotti
    with t1:
        st.header("Prodotti")
        # Filtro Category Text (default all first category)
        cats = sorted(df_prod['category_text'].dropna().unique()) if 'category_text' in df_prod.columns else []
        if cats:
            sel_cat = st.selectbox("Category Text", cats, index=0)
            df_cat = df_prod[df_prod['category_text']==sel_cat]
        else:
            sel_cat = None
            df_cat = df_prod.copy()

        # Filtro SKU sul subset di categoria
        skus = sorted(df_cat['prod_stripped'].dropna().unique())
        sel_sku = st.selectbox("Filtra per SKU", [""] + skus)
        df_view = df_cat[df_cat['prod_stripped']==sel_sku] if sel_sku else df_cat

        # Selezione colonne e visualizzazione
        if sel_cat:
            available = col_map.get(sel_cat, [])
            sel_cols = st.multiselect("Colonne da mostrare", available, default=available)
            if sel_cols:
                st.dataframe(df_view[sel_cols].reset_index(drop=True), use_container_width=True)
        else:
            st.info("Nessuna Category Text disponibile.")

    # Tab Riferimenti
    with t2:
        st.header("Riferimenti Originali")
        df_r = df_ref_orig.copy()
        brands = sorted(df_r['company_name'].dropna().unique())
        refs   = sorted(df_r['relation_code'].dropna().unique())
        f_b = st.multiselect("Brand", brands)
        f_r = st.multiselect("Reference", refs)
        if f_b: df_r = df_r[df_r['company_name'].isin(f_b)]
        if f_r: df_r = df_r[df_r['relation_code'].isin(f_r)]
        st.dataframe(df_r, use_container_width=True)

    # Tab Applicazioni
    with t3:
        st.header("Applicazioni Macchine")
        df_a = df_apps.copy()
        b_apps = sorted(df_a['brand_app'].dropna().unique())
        r_apps = sorted(df_a['reference_app'].dropna().unique())
        f_ba = st.multiselect("Brand Applicazione", b_apps)
        f_ra = st.multiselect("Reference Applicazione", r_apps)
        if f_ba: df_a = df_a[df_a['brand_app'].isin(f_ba)]
        if f_ra: df_a = df_a[df_a['reference_app'].isin(f_ra)]
        st.dataframe(df_a, use_container_width=True)

st.markdown("---")
st.write("© 2025 Dashboard Prodotti & Applicazioni")
