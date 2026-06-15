"""
Content Architect Agent - Creator of multilingual marketing content.

This agent is responsible for:
1. Generating Arabic ad copy (culturally appropriate, persuasive)
2. Generating English ad copy (professional, clear)
3. Creating product descriptions
4. Maintaining brand consistency
5. Ensuring compliance (no misleading claims)
"""

from typing import Dict, Any, List
from datetime import datetime

from src.core.abstractions import (
    Agent, AgentCapabilities, AgentRole, AgentState,
    Message, MessageType,
    Tool, ToolExecutionResult, ToolParameter, ToolCategory,
)


class ContentGenerationTool(Tool):
    """
    Tool for generating multilingual content using LLM.
    
    This is a mock implementation. In production, it would call OpenAI,
    Anthropic, or local LLM service.
    
    Input:
    {
        "content_type": "ad_copy" | "product_description" | "testimonial",
        "product_name": "Samsung Galaxy S25",
        "product_description": "Latest flagship phone...",
        "target_language": "ar" | "en",
        "tone": "professional" | "casual" | "urgent",
        "channel": "meta_facebook" | "whatsapp" | "email",
    }
    
    Output:
    {
        "content": "Generated text",
        "tokens_used": 150,
        "confidence": 0.95,
    }
    """
    
    def __init__(self):
        super().__init__(
            name="content_generation",
            description="Generate multilingual marketing content",
            category=ToolCategory.LLM_GENERATION,
            parameters=[
                ToolParameter(
                    name="content_type",
                    type="string",
                    description="Type of content (ad_copy, product_description, etc)",
                    required=True,
                    allowed_values=["ad_copy", "product_description", "testimonial", "faq"],
                ),
                ToolParameter(
                    name="product_name",
                    type="string",
                    description="Product name",
                    required=True,
                ),
                ToolParameter(
                    name="target_language",
                    type="string",
                    description="Target language (ar/en)",
                    required=True,
                    allowed_values=["ar", "en"],
                ),
                ToolParameter(
                    name="tone",
                    type="string",
                    description="Tone of content",
                    required=False,
                    default="professional",
                    allowed_values=["professional", "casual", "urgent", "friendly"],
                ),
            ],
        )
    
    async def _execute_impl(self, **kwargs) -> ToolExecutionResult:
        """Generate content (mock implementation)."""
        try:
            content_type = kwargs.get("content_type", "ad_copy")
            product_name = kwargs.get("product_name", "")
            language = kwargs.get("target_language", "ar")
            tone = kwargs.get("tone", "professional")
            
            # Mock content generation
            if language == "ar":
                if content_type == "ad_copy":
                    content = f"اكتشف {product_name} الآن! 🔥\n✨ أفضل العروض حصريّاً في رمضان\n🚚 توصيل مجاني + ضمان"
                elif content_type == "product_description":
                    content = f"{product_name} - أحدث تكنولوجيا مع جودة عالية.\nمثالي للاستخدام اليومي والعملي."
                else:
                    content = f"محتوى باللغة العربية عن {product_name}"
            else:  # English
                if content_type == "ad_copy":
                    content = f"Discover {product_name} Today! 🔥\n✨ Best Deals Exclusively in Ramadan\n🚚 Free Shipping + Warranty"
                elif content_type == "product_description":
                    content = f"{product_name} - Latest technology with premium quality.\nPerfect for everyday use."
                else:
                    content = f"English content about {product_name}"
            
            return ToolExecutionResult(
                success=True,
                data={
                    "content": content,
                    "language": language,
                    "content_type": content_type,
                    "tokens_used": 150,
                    "confidence": 0.95,
                },
                metadata={
                    "execution_time_ms": 1200,
                    "model": "mock-llm-v1",
                },
            )
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=str(e),
            )


class BrandConsistencyCheckTool(Tool):
    """
    Tool to verify content aligns with brand guidelines.
    
    Checks:
    - Brand voice consistency
    - No misleading claims
    - Proper tone for target audience
    - No prohibited words/phrases
    """
    
    def __init__(self):
        super().__init__(
            name="brand_consistency",
            description="Check content for brand consistency and compliance",
            category=ToolCategory.COMPLIANCE_CHECK,
            parameters=[
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to check",
                    required=True,
                ),
                ToolParameter(
                    name="brand_guidelines",
                    type="dict",
                    description="Brand guidelines to check against",
                    required=True,
                ),
            ],
        )
    
    async def _execute_impl(self, **kwargs) -> ToolExecutionResult:
        """Check content for brand consistency."""
        try:
            content = kwargs.get("content", "")
            guidelines = kwargs.get("brand_guidelines", {})
            
            issues = []
            
            # Mock checks
            if "100%" in content or "guarantee" in content.lower():
                issues.append({
                    "type": "misleading_claim",
                    "message": "Content contains absolute claims",
                    "severity": "warning",
                })
            
            if len(content) < 10:
                issues.append({
                    "type": "too_short",
                    "message": "Content is too short",
                    "severity": "error",
                })
            
            return ToolExecutionResult(
                success=True,
                data={
                    "is_compliant": len(issues) == 0,
                    "issues": issues,
                    "score": 95 if len(issues) == 0 else 70,
                },
            )
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=str(e),
            )


class ContentArchitectAgent(Agent):
    """
    Content Architect - Creates multilingual marketing content.
    
    Responsibilities:
    1. Generate Arabic and English ad copy
    2. Create product descriptions
    3. Ensure brand consistency
    4. Check compliance
    """
    
    def __init__(self, agent_id: str = "content_architect"):
        capabilities = AgentCapabilities(
            name="Content Architect",
            description="Creates multilingual marketing content (AR/EN)",
            role=AgentRole.CONTENT_GENERATOR,
            tools={"content_generation", "brand_consistency"},
            max_iterations=5,
            timeout_seconds=300,
        )
        
        tools = {
            "content_generation": ContentGenerationTool(),
            "brand_consistency": BrandConsistencyCheckTool(),
        }
        
        super().__init__(
            agent_id=agent_id,
            capabilities=capabilities,
            allowed_tools=tools,
        )
        
        # Content memory
        self._generated_content: Dict[str, List[Dict[str, Any]]] = {
            "ar": [],
            "en": [],
        }
        self._brand_guidelines: Dict[str, Any] = {}
    
    async def process_message(self, message: Message) -> Message:
        """
        Main decision loop for Content Architect.
        
        Handles:
        - TASK_REQUEST: New content creation task
        - TASK_RESPONSE: Acknowledgments
        """
        self._set_state(AgentState.THINKING)
        
        try:
            message_type = message.message_type
            content = message.content
            
            if message_type == MessageType.TASK_REQUEST:
                return await self._handle_content_request(message)
            
            else:
                return message.create_response(
                    response_type=MessageType.ERROR,
                    sender_id=self.agent_id,
                    content={"error": f"Unknown message type: {message_type}"},
                )
        
        except Exception as e:
            self._set_state(AgentState.ERROR)
            return message.create_response(
                response_type=MessageType.ERROR,
                sender_id=self.agent_id,
                content={"error": str(e)},
            )
    
    async def _handle_content_request(self, message: Message) -> Message:
        """Handle a content generation request."""
        content = message.content
        
        # Extract parameters
        products = content.get("products", [])
        languages = content.get("languages", ["ar", "en"])
        content_types = content.get("content_types", ["ad_copy", "product_description"])
        tone = content.get("tone", "professional")
        brand_guidelines = content.get("brand_guidelines", {})
        
        self._brand_guidelines = brand_guidelines
        
        generated_content = {}
        
        # Generate content for each product
        for product in products:
            product_id = product.get("product_id", "unknown")
            product_name = product.get("name_ar", product.get("name_en", "Product"))
            
            generated_content[product_id] = []
            
            # For each language
            for language in languages:
                # For each content type
                for content_type in content_types:
                    # Generate content
                    gen_result = await self.execute_tool(
                        "content_generation",
                        content_type=content_type,
                        product_name=product_name,
                        target_language=language,
                        tone=tone,
                    )
                    
                    if gen_result.success:
                        generated_text = gen_result.data.get("content", "")
                        
                        # Check compliance
                        check_result = await self.execute_tool(
                            "brand_consistency",
                            content=generated_text,
                            brand_guidelines=brand_guidelines,
                        )
                        
                        content_item = {
                            "content_type": content_type,
                            "language": language,
                            "content": generated_text,
                            "is_compliant": check_result.data.get("is_compliant", False),
                            "compliance_issues": check_result.data.get("issues", []),
                            "tokens": gen_result.data.get("tokens_used", 0),
                        }
                        
                        generated_content[product_id].append(content_item)
                        
                        # Store in memory
                        self._generated_content[language].append(content_item)
        
        self._set_state(AgentState.COMPLETED)
        
        # Return response
        return message.create_response(
            response_type=MessageType.TASK_RESPONSE,
            sender_id=self.agent_id,
            content={
                "status": "content_generated",
                "products_processed": len(products),
                "content_items": sum(len(v) for v in generated_content.values()),
                "generated_content": generated_content,
            },
        )
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolExecutionResult:
        """Execute a tool."""
        self._set_state(AgentState.EXECUTING)
        
        if tool_name not in self.allowed_tools:
            return ToolExecutionResult(
                success=False,
                error=f"Tool {tool_name} not available",
            )
        
        tool = self.allowed_tools[tool_name]
        return await tool.execute(agent_id=self.agent_id, **kwargs)
    
    def get_memory_context(self, context_type: str = "short_term") -> Dict[str, Any]:
        """Get agent memory."""
        return {
            "content_generated_ar": len(self._generated_content["ar"]),
            "content_generated_en": len(self._generated_content["en"]),
            "brand_guidelines_loaded": bool(self._brand_guidelines),
        }
    
    def update_memory(self, key: str, value: Any, context_type: str = "short_term") -> None:
        """Update memory (placeholder)."""
        pass
