import streamlit as st
import pandas as pd
from pathlib import Path
import random

st.set_page_config(
    page_title="ИИ-помощник строителя",
    page_icon="👷‍♂️",
    layout="wide",
)

# ----------------------
# Paths setup
# ----------------------
BASE_PATH = Path(".")
FILE_BUILD = BASE_PATH / "build_safety.csv"
FILE_ZHKH = BASE_PATH / "zhkh_safety.csv"
FILE_ONTOLOGY = BASE_PATH / "construction_safety.csv"
FILE_README = BASE_PATH / "README.md"

def load_csv(path):
    if path.exists():
        df = pd.read_csv(path)
        if len(df.columns) >= 3:
            df.columns = ["subject", "predicate", "object"] + list(df.columns[3:])
        return df
    else:
        return pd.DataFrame(columns=["subject", "predicate", "object"])

@st.cache_data(ttl=1)
def load_data():
    df_build = load_csv(FILE_BUILD)
    df_zhkh = load_csv(FILE_ZHKH)
    df_ontology = load_csv(FILE_ONTOLOGY)

    # Load README text
    readme_text = ""
    if FILE_README.exists():
        with open(FILE_README, "r", encoding="utf-8") as f:
            readme_text = f.read()
    else:
        readme_text = "Файл README.md не найден."

    return df_build, df_zhkh, df_ontology, readme_text


df_build, df_zhkh, df_ontology, readme_text = load_data()

st.sidebar.title("👷‍♂️ ИИ-помощник строителя")
scenario = st.sidebar.radio(
    "Меню:",
    [
        "🧱 Плановый наряд (строительство)",
        "🧪 Тест по знанию ТБ",
        "🚨 Аварийные работы ЖКХ",
        "🏠 Плановые / заявочные работы ЖКХ",
        "📑 Анализатор нормативных требований",
        "⚙️ Редактор Базы Знаний (CSV)",
        "ℹ️ Как это работает?",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown("База знаний: онтологические триплеты по строительству и ЖКХ.")

# ----------------------
# Общие утилиты
# ----------------------
def get_objects(df, subjects, predicate_pattern):
    mask = df["subject"].isin(subjects) & df["predicate"].str.contains(predicate_pattern, regex=True)
    return df[mask]["object"].drop_duplicates().tolist()

def get_siz(df, subjects):
    return get_objects(df, subjects, "должен_носить|тип_СИЗ")

def get_hazards(df, subjects):
    return get_objects(df, subjects, "опасност|подвержен_риску")

def get_prework(df, subjects):
    return get_objects(df, subjects, "обязан_перед_работой|имеет_требование")

def get_during(df, subjects):
    return get_objects(df, subjects, "обязан_во_время_работы")

def get_postwork(df, subjects):
    return get_objects(df, subjects, "обязан_после_работы")

def get_prohibited(df, subjects):
    return get_objects(df, subjects, "строго_запрещено|запрещено")

# ----------------------
# Общие кандидаты для строительства
# ----------------------
if not df_build.empty:
    manual_work_subjects = ["Высотные", "Земляные", "Сварочные", "Погрузочно"]
    work_mask = df_build["predicate"].str.contains("РАБОТЫ_", regex=True, na=False)
    auto_work_subjects = df_build[work_mask]["subject"].drop_duplicates().tolist()
    all_subjects = set(df_build["subject"].dropna().unique())
    work_subjects = (set(auto_work_subjects) | set(manual_work_subjects)) & all_subjects
    work_candidates = sorted(work_subjects)

    role_candidates = sorted(df_build[df_build["predicate"].str.contains("должен_носить", na=False)]["subject"].drop_duplicates().tolist())
else:
    work_candidates = []
    role_candidates = []

# ----------------------
# Плановый наряд (строительство)
# ----------------------
if scenario == "🧱 Плановый наряд (строительство)":
    st.title("🧱 Плановый наряд и инструктаж (строительство)")
    st.markdown("Мастер выбирает **вид работ** и **роль работника**, а помощник формирует чек-лист по технике безопасности.")

    col1, col2 = st.columns(2)
    with col1:
        work_type = st.selectbox("🏗 Вид работ (строительство):", options=work_candidates)
    with col2:
        role = st.selectbox("👷‍♂️ Роль / профессия:", options=role_candidates)

    if st.button("Сформировать чек-лист по ТБ", type="primary") and work_type and role:
        subjects = [work_type, role]

        st.markdown("### 🧾 Чек-лист по технике безопасности")
        st.markdown(f"**Контекст:** Вид работ — `{work_type}`, Роль — `{role}`.")

        st.markdown("#### 👷‍♂️ Обязательные СИЗ")
        siz = get_siz(df_build, subjects)
        if siz:
            for i in siz:
                st.markdown(f"- {i}")
        else:
            st.info("Нет данных")

        st.markdown("#### ⚠️ Опасные факторы")
        hazards = get_hazards(df_build, subjects)
        if hazards:
            for i in hazards:
                st.markdown(f"- {i}")
        else:
            st.info("Нет данных")

        st.markdown("#### 📋 Перед началом работ")
        prework = get_prework(df_build, subjects)
        if prework:
            for i in prework:
                st.markdown(f"- {i}")
        else:
            st.info("Нет данных")

        st.markdown("#### 🛑 Строго запрещено")
        prohibited = get_prohibited(df_build, subjects)
        if prohibited:
            for i in prohibited:
                st.markdown(f"- {i}")
        else:
            st.info("Нет данных")

# ----------------------
# Тест по знанию ТБ
# ----------------------
elif scenario == "🧪 Тест по знанию ТБ":
    st.title("🧪 Тест по знанию ТБ (строительство)")
    st.markdown("Приложение сформирует простой тест с вопросами на внимательность.")

    col1, col2 = st.columns(2)
    with col1: work_type = st.selectbox("🏗 Вид работ:", options=work_candidates)
    with col2: role = st.selectbox("👷‍♂️ Роль / профессия:", options=role_candidates)

    def generate_quiz(df, work_type, role, num_questions=5):
        subjects = [role]
        facts = []
        for item in get_siz(df, subjects): facts.append({"question": f'Какое СИЗ обязательно для роли "{role}"?', "correct": item})
        for item in get_hazards(df, subjects): facts.append({"question": f'Какой фактор относится к опасностям для роли "{role}"?', "correct": item})

        if not facts: return []
        random.shuffle(facts)
        facts = facts[:num_questions]

        pool_mask = ~df["subject"].isin([role, work_type])
        pool_objects = df[pool_mask]["object"].drop_duplicates().tolist()

        questions = []
        for fact in facts:
            correct = fact["correct"]
            wrong_candidates = [x for x in pool_objects if x != correct]
            wrong_options = random.sample(wrong_candidates, 2) if len(wrong_candidates) >= 2 else wrong_candidates * 2
            options = [correct] + wrong_options
            random.shuffle(options)
            questions.append({"question": fact["question"], "options": options, "correct_index": options.index(correct)})
        return questions

    if "quiz_questions" not in st.session_state: st.session_state.quiz_questions = []

    if st.button("Сформировать тест по ТБ", type="primary") and work_type and role:
        st.session_state.quiz_questions = generate_quiz(df_build, work_type, role)
        st.session_state.quiz_answers = [None] * len(st.session_state.quiz_questions)

    questions = st.session_state.get("quiz_questions", [])
    if questions:
        st.markdown("### 📝 Вопросы теста")
        for i, q in enumerate(questions):
            st.markdown(f"**Вопрос {i+1}.** {q['question']}")
            st.session_state.quiz_answers[i] = st.radio("Выберите вариант:", options=q["options"], key=f"quiz_q_{i}", index=0)
            st.markdown("---")

        if st.button("Проверить результаты"):
            correct_count = sum([1 for i, q in enumerate(questions) if st.session_state.quiz_answers[i] == q["options"][q["correct_index"]]])
            st.success(f"Результат: {correct_count} из {len(questions)} правильных ответов.")

            with st.expander("Показать разбор вопросов"):
                for i, q in enumerate(questions):
                    correct_answer = q["options"][q["correct_index"]]
                    st.markdown(f"**Вопрос {i+1}.** {q['question']}")
                    st.markdown(f"- Ваш ответ: `{st.session_state.quiz_answers[i]}`")
                    st.markdown(f"- Правильный ответ: ✅ `{correct_answer}`")
                    st.markdown("---")

# ----------------------
# Аварийные работы ЖКХ
# ----------------------
elif scenario == "🚨 Аварийные работы ЖКХ":
    st.title("🚨 Аварийные работы ЖКХ")
    accident_type = st.selectbox("Тип аварии:", ["Прорыв труб в подвале жилого дома", "Авария в канализационном колодце"])
    st.markdown("**Ключевая роль:** `Слесарь`")

    if st.button("Получить план действий", type="primary"):
        subjects = ["Слесарь", "Работы В", "Загазованность"]
        if "подвале" in accident_type: subjects.append("Затопление")

        st.markdown("### 🧾 Экстренная карточка работ")
        st.markdown("#### ⚠️ Специфические опасности")
        for item in get_hazards(df_zhkh, subjects): st.markdown(f"- {item}")

        st.markdown("#### 👷‍♂️ Специфические СИЗ для аварий")
        for item in get_siz(df_zhkh, subjects): st.markdown(f"- {item}")

        st.markdown("#### ⚡ Требования и немедленные действия")
        if not df_zhkh.empty:
            actions = df_zhkh[df_zhkh["subject"].isin(["Работы В", "Аварийные Работы"]) & df_zhkh["predicate"].str.contains("имеет_требование", na=False)]["object"].drop_duplicates()
            for item in actions: st.markdown(f"- {item}")

# ----------------------
# Плановые / заявочные работы ЖКХ
# ----------------------
elif scenario == "🏠 Плановые / заявочные работы ЖКХ":
    st.title("🏠 Плановые и заявочные работы ЖКХ")

    col1, col2 = st.columns(2)
    with col1: role = st.selectbox("👷‍♂️ Роль / профессия:", ["Слесарь", "Электрик", "Дворник", "Рабочий", "Оператор", "Мастер"])
    with col2: context = st.selectbox("🏢 Тип работ:", ["Плановое обслуживание", "Работы по заявке", "Работы на кровле", "Уборка территории"])

    if st.button("Сформировать чек-лист", type="primary"):
        subjects = [role]
        st.markdown("### 🧾 Чек-лист по ТБ")

        st.markdown("#### 👷‍♂️ Обязательные СИЗ")
        for item in get_siz(df_zhkh, subjects): st.markdown(f"- {item}")

        st.markdown("#### ⚠️ Типовые опасности")
        for item in get_hazards(df_zhkh, subjects): st.markdown(f"- {item}")

        st.markdown("#### 📋 Перед началом работ")
        for item in get_prework(df_zhkh, subjects): st.markdown(f"- {item}")

        st.markdown("#### 🛑 Строго запрещено")
        for item in get_prohibited(df_zhkh, subjects): st.markdown(f"- {item}")

        st.markdown("#### 📚 Инструктажи по ОТ (ЖКХ)")
        if not df_zhkh.empty:
            instr = df_zhkh[df_zhkh["subject"].isin(["Вводный Инструктаж", "Первичный", "Повторный", "Целевой"])]
            for subj in ["Вводный Инструктаж", "Первичный", "Повторный", "Целевой"]:
                sub_df = instr[instr["subject"] == subj]
                if not sub_df.empty:
                    st.markdown(f"**{subj}:**")
                    for _, row in sub_df.iterrows(): st.markdown(f"- {row['object']}")

# ----------------------
# Анализатор нормативных требований
# ----------------------
elif scenario == "📑 Анализатор нормативных требований":
    st.title("📑 Анализатор нормативных требований")
    st.markdown("Сценарий для инженеров ПТО: анализ применимого законодательства и глобальных рисков на основе расширенной онтологии ЖЦ объекта.")

    if df_ontology.empty:
        st.warning("⚠️ Файл `construction_safety_ontology_extended.csv` пуст или не загружен.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            object_types = ["Жилой_дом", "Промышленный_объект", "Общественное_здание"]
            obj_type = st.selectbox("🏢 Тип объекта:", options=object_types)
        with col2:
            lifecycle_stages = ["Проектирование", "Строительство", "Эксплуатация", "Снос"]
            stage = st.selectbox("🔄 Этап жизненного цикла:", options=lifecycle_stages)

        if st.button("Сформировать матрицу комплаенса", type="primary"):
            st.markdown(f"### 📊 Матрица комплаенса объекта")
            st.markdown(f"**Объект:** `{obj_type.replace('_', ' ')}` | **Этап:** `{stage}`")
            st.markdown("---")

            # 1. Законодательная база
            st.markdown("#### 📜 Применимое законодательство")
            obj_docs = df_ontology[(df_ontology["subject"] == obj_type) & (df_ontology["predicate"] == "основной_документ")]["object"].tolist()
            stage_docs = df_ontology[(df_ontology["subject"] == stage) & (df_ontology["predicate"] == "основные_правила")]["object"].tolist()
            all_docs = list(set(obj_docs + stage_docs))

            for doc in all_docs:
                st.markdown(f"- **{doc}**")
                doc_details = df_ontology[df_ontology["subject"] == doc]
                for _, row in doc_details.iterrows():
                    if row["predicate"] in ["регулирует", "статус"]:
                        st.markdown(f"  - _{row['predicate'].replace('_', ' ').capitalize()}:_ {row['object']}")

            # 2. Статус и надзор
            st.markdown("#### 🏛 Статус объекта и надзор")
            status_info = df_ontology[(df_ontology["subject"] == obj_type) & (df_ontology["predicate"].isin(["может_быть", "поднадзорен", "ключевое_требование"]))]["object"].tolist()
            if status_info:
                for info in status_info: st.markdown(f"- {info}")
            else:
                st.info("Специфических статусов надзора (например, ОПО) не зафиксировано.")

            # 3. Инженерные системы и их риски
            st.markdown("#### ⚙️ Инженерные системы и опасности")
            systems = df_ontology[(df_ontology["subject"] == obj_type) & (df_ontology["predicate"] == "включает_систему")]["object"].tolist()
            global_hazards = df_ontology[(df_ontology["subject"] == obj_type) & (df_ontology["predicate"] == "частые_опасности")]["object"].tolist()

            if global_hazards:
                st.markdown("**Глобальные риски объекта:** " + ", ".join(global_hazards))

            if systems:
                for sys in systems:
                    st.markdown(f"- **{sys}**")
                    sys_hazards = df_ontology[(df_ontology["subject"] == sys.replace(" ", "_")) & (df_ontology["predicate"] == "имеет_опасность")]["object"].tolist()
                    if sys_hazards:
                        st.markdown(f"  - _Риски:_ {', '.join(sys_hazards)}")
            else:
                st.info("Специфические инженерные системы не найдены.")

            # 4. Общие организационные меры
            st.markdown("#### 📋 Организационные меры и допуски (Макро-уровень)")
            org_measures = df_ontology[df_ontology["object"] == "Организационная мера"]["subject"].tolist()
            for measure in org_measures:
                st.markdown(f"- **{measure.replace('_', ' ')}**")
                measure_details = df_ontology[(df_ontology["subject"] == measure) & (df_ontology["predicate"] == "обязательно_для")]["object"].tolist()
                if measure_details:
                    st.markdown(f"  - _Обязательно для:_ {', '.join(measure_details)}")

# ----------------------
# РЕДАКТОР БАЗЫ ЗНАНИЙ (CSV)
# ----------------------
elif scenario == "⚙️ Редактор Базы Знаний (CSV)":
    st.title("⚙️ Встроенный редактор онтологии (CSV)")
    st.markdown("Здесь вы можете редактировать связи (триплеты) в базе знаний.")

    st.info("💡 **Как это работает в облаке:** Внесите изменения в таблицу ниже, затем нажмите кнопку **«Скачать измененный CSV»**. Скачанный файл вы сможете загрузить в свой репозиторий GitHub для постоянного обновления базы.")

    file_mapping = {
        "Строительство (.csv)": (FILE_BUILD, df_build),
        "ЖКХ (.csv)": (FILE_ZHKH, df_zhkh),
        "Макро-уровень (.csv)": (FILE_ONTOLOGY, df_ontology)
    }

    selected_file = st.selectbox("📂 Выберите базу данных для редактирования:", list(file_mapping.keys()))
    file_path, df_selected = file_mapping[selected_file]

    st.markdown(f"**Редактируется файл:** `{file_path.name}`")

    edited_df = st.data_editor(
        df_selected,
        num_rows="dynamic",
        use_container_width=True,
        key=f"editor_{file_path.name}"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Сохранить локально (только для ПК)", type="primary"):
            try:
                edited_df.to_csv(file_path, index=False)
                st.success(f"✅ Файл `{file_path.name}` успешно сохранен на вашем компьютере!")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"❌ Ошибка при сохранении: {e}")

    with col2:
        csv_data = edited_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Скачать измененный CSV (для Облака)",
            data=csv_data,
            file_name=file_path.name,
            mime="text/csv",
            type="primary"
        )

# ----------------------
# КАК ЭТО РАБОТАЕТ (README)
# ----------------------
elif scenario == "ℹ️ Как это работает?":
    st.title("ℹ️ Справка о проекте")
    st.markdown(readme_text)
