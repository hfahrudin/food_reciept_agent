from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate


def retrieve_by_date_range(db_connection, start_date: str, end_date: str):
    """Retrieve receipts between start_date and end_date (inclusive)"""
    query = """
    SELECT * FROM receipts
    WHERE date BETWEEN ? AND ?
    ORDER BY date
    """
    cursor = db_connection.execute(query, (start_date, end_date))
    return [dict(row) for row in cursor.fetchall()]


entry_node_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "You are an AI assistant. Read the user's messages and determine the next action. "
        "Return a JSON object with a single key 'action' whose value is either 'RETRIEVE' or 'RESPOND'. "
        "- 'RETRIEVE' if the query requires fetching receipts or external documents. "
        "- 'RESPOND' if the query can be answered directly. "
        "Do not include any explanation or extra text — only the JSON."
    ),
    HumanMessagePromptTemplate.from_template(
        "{chat_history}"
    )
])


not_retrieved_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "You are a helpful assistant. You could not understand the user's query or it is outside your scope. "
        "Respond politely and clearly, indicating that you are unable to provide an answer for this request. "
        "Do not mention receipts, purchases, or any unrelated assumptions."
    ),
    HumanMessagePromptTemplate.from_template("{chat_history}")
])

# Case 2: RETRIEVED but empty list
retrieved_empty_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "You are a helpful assistant. Receipts were retrieved, but no relevant items were found for the user's query."
        "Respond politely and inform the user that no items match the request."
    ),
    HumanMessagePromptTemplate.from_template("{chat_history}")
])

# Case 3: RETRIEVED with non-empty list
retrieved_with_items_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "You are a helpful assistant. Receipts were retrieved successfully and contain relevant items."
        "Generate a clear, concise response summarizing the purchased items for the user."
    ),
    HumanMessagePromptTemplate.from_template(
        "Chat history: {chat_history}\nRetrieved receipts: {retrieved_receipts}"
    )
])