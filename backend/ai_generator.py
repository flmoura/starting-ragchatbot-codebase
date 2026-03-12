import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for searching course information.

Tool Usage:
- **Outline/structure questions** (e.g. "What is the outline of X?", "What lessons does X have?"): Use `get_course_outline` — always return the course title, course link, and every lesson with its number and title
- **Content/detail questions** (e.g. "What does lesson 3 cover?"): Use `search_course_content`
- **Up to 2 sequential tool calls per query** — use a second call only when the first result is insufficient to fully answer the question. Do not repeat a tool call with identical parameters.
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific questions**: Use the appropriate tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results"

For outline responses, always include:
1. Course title
2. Course link (if available)
3. All lessons listed as: Lesson <number>: <title>

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)
        
        # Return direct response
        block = response.content[0]
        return block.text if block.type == "text" else ""
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager, rounds_remaining: int = 2):
        """
        Handle execution of tool calls with support for sequential rounds.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            rounds_remaining: How many tool-call rounds are still allowed (default 2)

        Returns:
            Final response text after tool execution
        """
        messages = base_params["messages"].copy()
        response = initial_response

        while True:
            # Append current assistant tool-use message
            messages.append({"role": "assistant", "content": response.content})

            # Execute all tool calls in this response
            tool_results = []
            for content_block in response.content:
                if content_block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(
                            content_block.name,
                            **content_block.input
                        )
                    except Exception as e:
                        result = f"Tool execution failed: {e}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": result
                    })

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            rounds_remaining -= 1

            # Build next call params; include tools only if another round is possible
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"]
            }
            if rounds_remaining > 0:
                next_params["tools"] = base_params["tools"]
                next_params["tool_choice"] = base_params["tool_choice"]

            response = self.client.messages.create(**next_params)

            # Stop if Claude is done or we've exhausted rounds
            if response.stop_reason != "tool_use" or rounds_remaining == 0:
                break

        return response.content[0].text if response.content else ""