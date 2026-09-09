import os
from typing import Literal, TypedDict

import wikipedia
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openrouter import ChatOpenRouter
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

load_dotenv()

MODEL_NAME = os.environ["OPENROUTER_MODEL"]
API_KEY = os.environ["OPENROUTER_API_KEY"]
MAX_TOOL_ITERATIONS = 4

wikipedia.set_lang("en")
wikipedia.set_user_agent("IntentRouterAgentBlog/1.0 (AIGuru blog demo; contact: hello@aiguru.local)")

llm = ChatOpenRouter(model=MODEL_NAME, api_key=API_KEY, temperature=0)


class IntentClassification(BaseModel):
    intent: Literal["knowledge", "calculation", "out_of_scope"]


class AgentState(TypedDict):
    question: str
    intent: str
    answer: str
    trace: list[str]


@tool
def wikipedia_search(query: str) -> str:
    """Tra cứu Wikipedia để lấy thông tin thực tế kèm nguồn trích dẫn, số liệu hoặc sự kiện cần kiểm chứng.
    Wikipedia đang được cấu hình bằng tiếng Anh, nên query truyền vào phải luôn viết bằng tiếng Anh,
    kể cả khi câu hỏi gốc là tiếng Việt."""
    try:
        page = wikipedia.page(query, auto_suggest=True)
    except wikipedia.exceptions.DisambiguationError as exc:
        return f"Từ khoá không rõ ràng, các lựa chọn gần nhất: {', '.join(exc.options[:5])}"
    except wikipedia.exceptions.PageError:
        return f"Không tìm thấy trang Wikipedia nào khớp với '{query}'"
    except Exception as exc:
        return f"Lỗi khi tra cứu Wikipedia (mạng hoặc timeout): {exc}"

    sentences = page.summary.split(". ")
    short_summary = ". ".join(sentences[:3]).rstrip(".") + "."
    return f"{short_summary}\nNguồn: {page.title} ({page.url})"


@tool
def add(a: float, b: float) -> float:
    """Cộng hai số."""
    return a + b


@tool
def subtract(a: float, b: float) -> float:
    """Lấy a trừ b và trả về a - b."""
    return a - b


@tool
def multiply(a: float, b: float) -> float:
    """Nhân hai số."""
    return a * b


@tool
def divide(a: float, b: float) -> float:
    """Chia số a cho số b (a / b)."""
    if b == 0:
        raise ValueError("Không thể chia cho 0")
    return a / b


KNOWLEDGE_TOOLS = [wikipedia_search]
CALCULATION_TOOLS = [add, subtract, multiply, divide]


def classify_intent(state: AgentState) -> dict:
    structured_llm = llm.with_structured_output(IntentClassification)
    system = SystemMessage(
        content=(
            "Bạn là bộ phân loại ý định câu hỏi, chỉ được chọn đúng một trong ba nhãn. "
            "Trả về 'knowledge' nếu câu hỏi thuộc dạng hỏi đáp kiến thức (sự kiện, "
            "khái niệm, con người, địa lý, lịch sử...), kể cả khi câu hỏi có kèm "
            "nhiều số liệu nhưng bản chất câu hỏi thật sự vẫn là hỏi kiến thức. "
            "Trả về 'calculation' nếu câu hỏi yêu cầu thực hiện phép tính cộng, "
            "trừ, nhân, chia dựa trên các dữ kiện số học đã cho, kể cả khi dữ "
            "kiện được lồng trong một câu chuyện hay tình huống. Trả về "
            "'out_of_scope' cho mọi câu hỏi khác không thuộc hai nhóm trên, "
            "ví dụ yêu cầu viết code, dịch thuật, trò chuyện thông thường, xin "
            "lời khuyên, hoặc câu hỏi ghép hai yêu cầu tách biệt ngang hàng "
            "nhau (một ý hỏi kiến thức và một ý hỏi tính toán không liên quan "
            "tới nhau)."
        )
    )
    result = structured_llm.invoke([system, HumanMessage(content=state["question"])])
    return {
        "intent": result.intent,
        "trace": state["trace"] + [f"classify_intent -> {result.intent}"],
    }


def _run_tool_loop(state: AgentState, tools: list, system_prompt: str) -> dict:
    tools_by_name = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["question"]),
    ]
    trace = list(state["trace"])

    for _ in range(MAX_TOOL_ITERATIONS):
        response: AIMessage = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            return {"answer": response.content, "trace": trace + ["final_answer"]}

        for call in response.tool_calls:
            tool_fn = tools_by_name[call["name"]]
            try:
                result = tool_fn.invoke(call["args"])
            except Exception as exc:
                result = f"Lỗi khi thực thi tool: {exc}"
            trace.append(f"tool_call {call['name']}({call['args']}) -> {result}")
            messages.append(
                ToolMessage(content=str(result), tool_call_id=call["id"], name=call["name"])
            )

    final = llm.invoke(messages)
    return {
        "answer": final.content,
        "trace": trace + ["final_answer (forced after max iterations)"],
    }


def knowledge_node(state: AgentState) -> dict:
    system_prompt = (
        "Bạn là trợ lý hỏi đáp kiến thức. Ưu tiên trả lời bằng kiến thức sẵn có của bạn. "
        "Chỉ gọi công cụ wikipedia_search khi câu hỏi cần số liệu, ngày tháng hoặc sự kiện "
        "cụ thể mà bạn không chắc chắn. Nếu đã gọi wikipedia_search nhưng kết quả trả về "
        "không chứa thông tin cần thiết để trả lời, hãy nói rõ là bạn không tìm thấy thông "
        "tin đó, tuyệt đối không tự suy đoán hay trả lời dựa trên kiến thức có sẵn của mình "
        "trong trường hợp này. Nếu đã gọi wikipedia_search và tìm được thông tin phù hợp, "
        "luôn nêu rõ nguồn (tên trang và URL) ở cuối câu trả lời. Trả lời ngắn gọn bằng "
        "tiếng Việt."
    )
    return _run_tool_loop(state, KNOWLEDGE_TOOLS, system_prompt)


def calculation_node(state: AgentState) -> dict:
    system_prompt = (
        "Bạn là trợ lý tính toán. Luôn dùng các công cụ add, subtract, multiply, divide để "
        "thực hiện phép tính, không tự nhẩm bằng suy luận ngôn ngữ. "
        "Với biểu thức nhiều bước, gọi tool tuần tự từng bước một. "
        "Trả lời ngắn gọn bằng tiếng Việt, nêu rõ kết quả cuối."
    )
    return _run_tool_loop(state, CALCULATION_TOOLS, system_prompt)


def out_of_scope_node(state: AgentState) -> dict:
    system_prompt = (
        "Bạn là trợ lý chỉ hỗ trợ đúng hai loại yêu cầu: hỏi đáp kiến thức và "
        "tính toán số học. Câu hỏi hiện tại không thuộc hai loại đó. Hãy từ "
        "chối trả lời một cách lịch sự và ngắn gọn bằng tiếng Việt, giải "
        "thích rằng bạn chỉ hỗ trợ hai loại yêu cầu trên."
    )
    response = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=state["question"])]
    )
    return {
        "answer": response.content,
        "trace": state["trace"] + ["out_of_scope_node -> declined"],
    }


def route_by_intent(state: AgentState) -> str:
    return state["intent"]


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("knowledge", knowledge_node)
    builder.add_node("calculation", calculation_node)
    builder.add_node("out_of_scope", out_of_scope_node)

    builder.add_edge(START, "classify_intent")
    builder.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "knowledge": "knowledge",
            "calculation": "calculation",
            "out_of_scope": "out_of_scope",
        },
    )
    builder.add_edge("knowledge", END)
    builder.add_edge("calculation", END)
    builder.add_edge("out_of_scope", END)

    return builder.compile()


graph = build_graph()
