import streamlit as st
from PIL import Image
import time
import re
from datetime import datetime, timedelta
from storage import load_inventory, save_inventory
from llm_utils import ask_llm, safe_json_parse
from ocr_utils import preprocess_image, extract_text_multiconfig, parse_expiry_date

st.set_page_config(page_title="Smart Expiry Tracker", page_icon="🧾", layout="wide")

st.title("Smart Expiry Tracker")
st.markdown("*LLM-powered grocery inventory management*")

if "products" not in st.session_state:
    st.session_state["products"] = load_inventory()
if 'temp_product' not in st.session_state:
    st.session_state.temp_product = None

menu = ["Add Product", "View Inventory", "Usage Planner"]
choice = st.radio("Navigation", menu, horizontal=True)

if choice == "Add Product":
    st.header("Add New Product")
    
    product_type = st.radio(
        "Product Type:",
        ["Packaged (with label & expiry)", "Fresh Produce (manual entry)"],
        horizontal=True
    )
    
    is_fresh_produce = (product_type == "Fresh Produce (manual entry)")
    
    if not is_fresh_produce:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Product Label")
            uploaded_file1 = st.file_uploader(
                "Upload product front label", 
                type=["jpg", "png", "jpeg"],
                key="product_img"
            )
            if uploaded_file1:
                img1 = Image.open(uploaded_file1)
                st.image(img1, caption=f"Original: {uploaded_file1.name}", use_column_width=True)
        
        with col2:
            st.subheader("Expiry Label")
            uploaded_file2 = st.file_uploader(
                "Upload expiry date label", 
                type=["jpg", "png", "jpeg"],
                key="expiry_img"
            )
            if uploaded_file2:
                img2 = Image.open(uploaded_file2)
                st.image(img2, caption=f"Original: {uploaded_file2.name}", use_column_width=True)

        if uploaded_file1 and uploaded_file2:
            
            if st.button("Process Images", type="primary", use_container_width=True):
                
                st.session_state.temp_product = None
                
                with st.spinner("Processing..."):
                    
                    proc_img1 = preprocess_image(img1, mode="product")
                    proc_img2 = preprocess_image(img2, mode="expiry")
                    
                    text1 = extract_text_multiconfig(proc_img1)
                    text2 = extract_text_multiconfig(proc_img2)
                    
                    product_prompt = f"""IMPORTANT: This is a NEW product analysis. Forget any previous products.

I will show you OCR text from a product label. The text may be in GERMAN or English.

OCR Text from Product Label:
'''
{text1}
'''

CRITICAL: If you see German words, translate them:
- REIS = Rice
- BASMATI-REIS or BASMATI REIS = Basmati Rice
- KAFFEE = Coffee
- MILCH = Milk
- ZUCKER = Sugar

Product Type Keywords:
- Rice: RICE, REIS, BASMATI, JASMINE, BASMATI-REIS
- Coffee: COFFEE, KAFFEE, ESPRESSO
- Tea: TEA, TEE, CHAI
- Spice: MASALA, CURRY, GEWÜRZ
- Dairy: MILK, MILCH, YOGURT, KÄSE

Task:
1. Look at the OCR text - do you see "BASMATI" or "REIS"?
2. If YES → name="Basmati Reis", category="Rice/Grains"
3. Find quantity like "1kg", "500g", "1 kg", "500 g"

Examples:
- OCR has "aromatischer BASMATI-REIS 1kg" → name="Basmati Reis", category="Rice/Grains", quantity="1kg"
- OCR has "MACCOFFEE 100g" → name="MacCoffee", category="Coffee", quantity="100g"

Return ONLY JSON:
{{
  "name": "product name",
  "category": "category",
  "quantity": "amount or Unknown"
}}

JSON:"""

                    product_response = ask_llm(product_prompt)
                    product_data = safe_json_parse(product_response)
                    
                    name = product_data.get("name", "Unknown Product")
                    category = product_data.get("category", "Unknown Category")
                    quantity = product_data.get("quantity", "Unknown")
                    
                    expiry_date = parse_expiry_date(text2)
                    
                    if not expiry_date:
                        expiry_prompt = f"""Extract expiry date from OCR text.

OCR Text:
{text2}

Patterns to look for:
- 02.2027 → February 2027
- EXP: OCT-2025 → October 2025
- MHD: 05.2026 → May 2026
- DEC 2027 → December 2027

IMPORTANT: If only month and year are given (e.g., "OCT 2025"), use the LAST day of that month.

Examples:
- OCT 2025 → 2025-10-31 (October has 31 days)
- FEB 2026 → 2026-02-28 (February has 28 days in non-leap year)
- APR 2027 → 2027-04-30 (April has 30 days)

Return ONLY valid JSON:
{{
  "expiry": "DD-MM-YYYY"
}}

JSON:"""
                        expiry_response = ask_llm(expiry_prompt)
                        expiry_data = safe_json_parse(expiry_response)
                        raw_expiry = expiry_data.get("expiry", "Unknown")
                        
                        if raw_expiry and raw_expiry != "Unknown":
                            try:
                                exp_dt = datetime.strptime(raw_expiry, "%d-%m-%Y")
                                if exp_dt.day == 1:
                                    year = exp_dt.year
                                    month = exp_dt.month
                                    from calendar import monthrange
                                    last_day = monthrange(year, month)[1]
                                    expiry_date = f"{last_day:02d}-{month:02d}-{year}"
                                else:
                                    expiry_date = raw_expiry
                            except:
                                expiry_date = raw_expiry
                        else:
                            expiry_date = "Unknown"
                    
                    st.success("Extraction Complete")
                    
                    st.markdown("### Extracted Information")
                    result_col1, result_col2, result_col3, result_col4 = st.columns(4)
                    
                    with result_col1:
                        st.metric("Product Name", name)
                    with result_col2:
                        st.metric("Category", category)
                    with result_col3:
                        st.metric("Quantity", quantity)
                    with result_col4:
                        st.metric("Expiry Date", expiry_date if expiry_date else "Unknown")
                    
                    st.session_state.temp_product = {
                        'name': name,
                        'category': category,
                        'quantity': quantity,
                        'expiry': expiry_date if expiry_date else "Unknown"
                    }
        
        if st.session_state.get('temp_product'):
            st.markdown("---")
            st.markdown("### Review & Edit Information")
            
            product_data = st.session_state.temp_product
            
            edit_col1, edit_col2, edit_col3, edit_col4 = st.columns(4)
            
            with edit_col1:
                edited_name = st.text_input(
                    "Product Name:", 
                    value=product_data['name'], 
                    key="edit_name"
                )
            
            with edit_col2:
                categories = ["Rice/Grains", "Coffee", "Tea", "Spice Mix", "Dairy", 
                             "Canned Goods", "Sauce", "Fresh Produce", "Snacks", 
                             "Sugar", "Oil", "Pasta", "Other"]
                
                try:
                    default_index = categories.index(product_data['category'])
                except:
                    default_index = len(categories) - 1
                
                edited_category = st.selectbox(
                    "Category:", 
                    categories,
                    index=default_index,
                    key="edit_category"
                )
            
            with edit_col3:
                edited_quantity = st.text_input(
                    "Quantity:", 
                    value=product_data.get('quantity', 'Unknown'),
                    key="edit_quantity"
                )
            
            with edit_col4:
                edited_expiry = st.text_input(
                    "Expiry (DD-MM-YYYY):", 
                    value=product_data['expiry'],
                    key="edit_expiry"
                )
            
            save_col1, save_col2 = st.columns([1, 1])
            
            with save_col1:
                if st.button("Save to Inventory", type="primary", use_container_width=True):
                    if edited_name and edited_name.strip():
                        st.session_state["products"][edited_name] = {
                            "category": edited_category,
                            "quantity": edited_quantity,
                            "expiry": edited_expiry,
                            "added_date": datetime.now().strftime("%d-%m-%Y")
                        }
                        
                        if save_inventory(st.session_state["products"]):
                            st.success(f"{edited_name} added to inventory")
                        else:
                            st.warning(f"{edited_name} added but save failed")
                        
                        st.session_state.temp_product = None
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Please enter a product name")
            
            with save_col2:
                if st.button("Re-process Images", use_container_width=True):
                    st.session_state.temp_product = None
                    st.rerun()
    
    else:
        st.info("For fresh produce, manually enter product details")
        
        form_col1, form_col2 = st.columns(2)
        
        with form_col1:
            produce_name = st.text_input("Product Name (e.g., Onions, Tomatoes, Apples):")
            produce_quantity = st.number_input("Quantity:", min_value=1, value=1, step=1)
        
        with form_col2:
            produce_category = st.selectbox(
                "Category:",
                ["Vegetables", "Fruits", "Leafy Greens", "Herbs"]
            )
        
        if st.button("Estimate Expiry & Add", type="primary", use_container_width=True):
            if produce_name and produce_name.strip():
                with st.spinner("Estimating shelf life..."):
                    
                    expiry_prompt = f"""Estimate the typical shelf life for this fresh produce item when stored properly.

Product: {produce_name}
Category: {produce_category}
Quantity: {produce_quantity}

Provide a CONSERVATIVE estimate (minimum days before spoiling when refrigerated if needed).

Common guidelines:
- Leafy Greens: 3-5 days
- Root Vegetables (onions, potatoes, carrots): 7-21 days  
- Tomatoes: 5-7 days
- Fruits (apples, oranges): 5-10 days
- Berries: 3-5 days
- Herbs: 5-7 days

Today is {datetime.now().strftime('%Y-%m-%d')}.

Return ONLY valid JSON:
{{
  "days": number,
  "expiry": "DD-MM-YYYY",
  "storage_tip": "brief storage advice"
}}

JSON:"""
                    
                    expiry_response = ask_llm(expiry_prompt)
                    expiry_data = safe_json_parse(expiry_response)
                    
                    estimated_days = expiry_data.get("days", 7)
                    expiry_date = expiry_data.get("expiry", 
                        (datetime.now() + timedelta(days=estimated_days)).strftime('%d-%m-%Y'))
                    storage_tip = expiry_data.get("storage_tip", "Store in cool, dry place")
                    
                    st.success(f"Estimated shelf life: {estimated_days} days")
                    st.info(f"{storage_tip}")
                    
                    st.session_state["products"][produce_name] = {
                        "category": "Fresh Produce",
                        "quantity": f"{produce_quantity} units",
                        "expiry": expiry_date,
                        "added_date": datetime.now().strftime("%d-%m-%Y")
                    }
                    
                    if save_inventory(st.session_state["products"]):
                        st.success(f"{produce_name} (qty: {produce_quantity}) added")
                    else:
                        st.warning(f"{produce_name} added but save failed")
                    
                    time.sleep(1)
                    st.rerun()
            else:
                st.error("Please enter a product name")

elif choice == "View Inventory":
    st.header("Current Inventory")
    
    if st.session_state["products"]:
        
        expired_items = []
        for product_name, details in st.session_state["products"].items():
            expiry = details.get("expiry", "Unknown")
            if expiry and expiry != "Unknown":
                try:
                    expiry_date = datetime.strptime(expiry, "%d-%m-%Y")
                    days_left = (expiry_date - datetime.now()).days
                    if days_left < 0:
                        expired_items.append((product_name, abs(days_left)))
                except:
                    pass
        
        if expired_items:
            st.warning("Smart Removal Suggestions")
            for product_name, days_expired in expired_items:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"'{product_name}' expired {days_expired} days ago. Should I remove it?")
                with col2:
                    if st.button("Remove", key=f"remove_expired_{product_name}"):
                        del st.session_state["products"][product_name]
                        save_inventory(st.session_state["products"])
                        st.rerun()
            st.markdown("---")
        
        for idx, (product_name, details) in enumerate(st.session_state["products"].items()):
            
            expiry = details.get("expiry", "Unknown")
            quantity = details.get("quantity", "Unknown")
            days_left = "Unknown"
            urgency_color = "🔵"
            
            is_depleted = False
            if quantity != "Unknown":
                try:
                    qty_match = re.search(r'(\d+\.?\d*)', quantity)
                    if qty_match:
                        qty_value = float(qty_match.group(1))
                        if qty_value <= 0:
                            is_depleted = True
                            urgency_color = "🔴"
                except:
                    pass
            
            if expiry and expiry != "Unknown" and not is_depleted:
                try:
                    expiry_date = datetime.strptime(expiry, "%d-%m-%Y")
                    days_left = (expiry_date - datetime.now()).days
                    
                    if days_left < 0:
                        urgency_color = "🔴"
                        days_left = f"EXPIRED ({abs(days_left)} days ago)"
                    elif days_left < 3:
                        urgency_color = "🔴"
                        days_left = f"{days_left} days"
                    elif days_left < 7:
                        urgency_color = "🟠"
                        days_left = f"{days_left} days"
                    elif days_left < 30:
                        urgency_color = "🟡"
                        days_left = f"{days_left} days"
                    else:
                        urgency_color = "🟢"
                        days_left = f"{days_left} days"
                except:
                    pass
            
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 2])
                
                with col1:
                    st.markdown(f"### {urgency_color} {product_name}")
                    st.caption(f"Category: {details['category']} | Qty: {quantity}")
                    
                    if is_depleted:
                        st.error("OUT OF STOCK")
                
                with col2:
                    st.metric("Expiry", expiry if expiry else "Unknown")
                
                with col3:
                    st.metric("Days Left", days_left)
                
                if is_depleted:
                    st.warning("This item is out of stock. Would you like to remove it?")
                    col_deplete1, col_deplete2 = st.columns([1, 3])
                    with col_deplete1:
                        if st.button("Yes, Remove", key=f"deplete_remove_{idx}"):
                            del st.session_state["products"][product_name]
                            save_inventory(st.session_state["products"])
                            st.rerun()
                    with col_deplete2:
                        if st.button("No, Keep It", key=f"deplete_keep_{idx}"):
                            st.rerun()
                
                if st.button("🗑️ Delete", key=f"del_{idx}"):
                    del st.session_state["products"][product_name]
                    save_inventory(st.session_state["products"])
                    st.rerun()
                
                st.markdown("---")
    else:
        st.info("No products in inventory")

elif choice == "Usage Planner":
    st.header("Usage Planner")
    
    if st.session_state["products"]:
        
        st.subheader("Your Cooking Setup")
        pref_col1, pref_col2 = st.columns(2)
        
        with pref_col1:
            has_oven = st.checkbox("I have an oven", value=True)
            has_microwave = st.checkbox("I have a microwave", value=True)
            has_stovetop = st.checkbox("I have a stovetop", value=True)
        
        with pref_col2:
            cooking_skill = st.selectbox(
                "Cooking skill level",
                ["beginner", "intermediate", "advanced"],
                index=1
            )
        
        st.markdown("---")
        
        selected_product = st.selectbox(
            "Select Product:", 
            list(st.session_state["products"].keys())
        )
        
        if st.button("Generate Usage Plan", type="primary"):
            
            details = st.session_state["products"][selected_product]
            
            other_products = [p for p in st.session_state["products"].keys() if p != selected_product]
            inventory_list = ", ".join(other_products) if other_products else "No other products"
            
            equipment = []
            if has_stovetop:
                equipment.append("stovetop")
            if has_oven:
                equipment.append("oven")
            if has_microwave:
                equipment.append("microwave")
            equipment_str = ", ".join(equipment) if equipment else "only basic tools"
            
            with st.spinner("Creating plan..."):
                
                experts_prompt = f"""You are simulating THREE different expert perspectives to create the best usage plan.

Product: {selected_product}
Category: {details['category']}
Quantity: {details.get('quantity', 'Unknown')}
Expiry: {details['expiry']}
Current Date: {datetime.now().strftime('%Y-%m-%d')}
Other Products: {inventory_list}

EXPERT 1 - Nutrition Expert:
Focus on maximizing freshness and nutritional value. Prioritize using fresh produce quickly.

EXPERT 2 - Budget Optimizer:
Focus on preventing waste and using expensive items before they expire. Consider cost efficiency.

EXPERT 3 - Recipe Matcher:
Focus on creating delicious combinations with other available products. Make meal planning easy.

Now synthesize their advice into ONE unified usage plan that:
- Uses equipment: {equipment_str}
- Matches skill level: {cooking_skill}
- Provides 3-5 specific dates with meal ideas
- Explains which expert perspective influenced each suggestion

Format:
[Date]: Meal/dish name
- Why: [Which expert perspective - nutrition/budget/recipe]
- Combine with: [other products if any]
- Method: Brief prep note

Your plan:"""

                plan = ask_llm(experts_prompt)
                
                st.markdown(f"### Usage Plan for {selected_product}")
                st.markdown(plan)
                
                if st.button("Generate Different Plan", use_container_width=True):
                    st.rerun()
    else:
        st.warning("No products to plan for")
        st.info("Go to 'Add Product' to add items")

st.markdown("---")
st.caption("Tip: Make sure Ollama is running with llama3 model")