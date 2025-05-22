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
    st.sidebar.warning("📥 Carica tutti e tre i file per procedere.")
else:
    # ---- tutto il tuo preprocess + UI qui dentro ----
    df_prod, df_ref_orig, df_apps, col_map = preprocess()

    # Costanti per filtro SKU
    skus_list = sorted(df_prod['prod_stripped'].dropna().unique())

    # Tab UI…
    t1, t2, t3 = st.tabs(["Prodotti","Riferimenti","Applicazioni"])
    # …ecc. tutto il codice che hai già, ma indentato di un livello


# -------------------------------------------
# Funzioni di caching
# -------------------------------------------
@st.cache_data(show_spinner=False)
def load_df(f):
    return pd.read_excel(f, dtype=str)

@st.cache_data(show_spinner=False)
def preprocess():
    # Caricamento
    dp = load_df(prod_file)
    dr = load_df(ref_file)
    da = load_df(app_file)

    # Pivot riferimenti
    dr_temp = dr.copy()
    dr_temp['idx'] = dr_temp.groupby('code').cumcount() + 1
    dr_piv = dr_temp.pivot(index='code', columns='idx', values=['company_name','relation_code'])
    dr_piv.columns = [f"brand{i}" if c=='company_name' else f"reference{i}" for c,i in dr_piv.columns]
    dr_piv = dr_piv.reset_index().rename(columns={'code':'sku'})
    dr_piv['sku_stripped'] = dr_piv['sku'].str.lstrip('0')

    # Merge prodotti + riferimenti
    if 'product_code' in dp.columns:
        dp['prod_stripped'] = dp['product_code'].str.lstrip('0')
    dp_merged = dp.merge(dr_piv, left_on='prod_stripped', right_on='sku_stripped', how='left')

    # Mappa colonne per category_text
    col_map = {}
    if 'category_text' in dp_merged.columns:
        for cat in dp_merged['category_text'].dropna().unique():
            sub = dp_merged[dp_merged['category_text']==cat]
            # colonne con almeno un valore
            cols = [c for c in sub.columns if sub[c].notna().any() and sub[c].astype(str).str.strip().replace('','Nan').notnull().any()]
            col_map[cat] = cols

    # Preparazione applicazioni
    da['relation_code'] = da['relation_code'].fillna('')
    da_long = da.assign(reference_app=da['relation_code'].str.split(','))
    da_long = da_long.explode('reference_app')
    da_long['reference_app'] = da_long['reference_app'].str.strip()
    da_long = da_long[da_long['reference_app']!='']
    da_long = da_long.rename(columns={'company_name':'brand_app','code':'sku'})[['sku','brand_app','reference_app']]

    return dp_merged, dr, da_long, col_map

# Pre-elaborazione dati
df_prod, df_ref_orig, df_apps, col_map = preprocess()

# -------------------------------------------
# Costanti per filtro SKU
# -------------------------------------------
skus_list = sorted(df_prod['prod_stripped'].dropna().unique())

# -------------------------------------------
# UI Tabs
# -------------------------------------------
t1, t2, t3 = st.tabs(["Prodotti","Riferimenti","Applicazioni"])

# Tab Prodotti
with t1:
    st.header("Prodotti")
    # Filtro SKU fisso
    sel_sku = st.selectbox("Filtra per SKU", [""] + skus_list)
    df_view = df_prod[df_prod['prod_stripped']==sel_sku] if sel_sku else df_prod
    # Filtro Category Text
    if 'category_text' in df_view.columns:
        cats = sorted(df_view['category_text'].dropna().unique())
        sel_cat = st.selectbox("Category Text", [""] + cats)
        if sel_cat:
            df_view = df_view[df_view['category_text']==sel_cat]
    # Filtri dinamici colonne
    if sel_cat:
        available_cols = col_map.get(sel_cat, df_view.columns.tolist())
    else:
        available_cols = df_view.columns.tolist()
    sel_cols = st.multiselect("Colonne da mostrare", available_cols, default=available_cols)
    # Visualizzazione
    st.dataframe(df_view[sel_cols].reset_index(drop=True), use_container_width=True)

# Tab Riferimenti
with t2:
    st.header("Riferimenti Originali")
    dr = df_ref_orig.copy()
    # Filtri
    b_opts = sorted(dr['company_name'].dropna().unique())
    r_opts = sorted(dr['relation_code'].dropna().unique())
    sel_br = st.multiselect("Brand", b_opts)
    if sel_br:
        dr = dr[dr['company_name'].isin(sel_br)]
    sel_rr = st.multiselect("Reference", r_opts)
    if sel_rr:
        dr = dr[dr['relation_code'].isin(sel_rr)]
    st.dataframe(dr.reset_index(drop=True), use_container_width=True)

# Tab Applicazioni
with t3:
    st.header("Applicazioni Macchine")
    da_view = df_apps.copy()
    ba_opts = sorted(da_view['brand_app'].dropna().unique())
    ra_opts = sorted(da_view['reference_app'].dropna().unique())
    sel_ba = st.multiselect("Brand Applicazione", ba_opts)
    if sel_ba:
        da_view = da_view[da_view['brand_app'].isin(sel_ba)]
    sel_ra = st.multiselect("Reference Applicazione", ra_opts)
    if sel_ra:
        da_view = da_view[da_view['reference_app'].isin(sel_ra)]
    st.dataframe(da_view.reset_index(drop=True), use_container_width=True)

# Footer
st.markdown("---")
st.write("© 2025 Dashboard Prodotti & Applicazioni")
