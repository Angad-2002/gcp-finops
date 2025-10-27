"""LLM service for AI-powered FinOps insights using multiple AI providers."""

import os
from typing import Optional, Dict, Any, List, Union
from .types import DashboardData, AuditResult, OptimizationRecommendation
from .helpers import calculate_percentage_change

# Import AI providers
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class LLMService:
    """Service for AI-powered insights using multiple AI providers."""
    
    # Available providers and their models
    PROVIDERS = {
        "groq": {
            "name": "Groq",
            "description": "Fast inference with open-source models",
            "available": GROQ_AVAILABLE,
            "models": {
                "llama-3.3-70b-versatile": {
                    "name": "Llama 3.3 70B Versatile",
                    "description": "Meta's latest versatile model - best for complex analysis",
                    "context_window": 32768,
                    "recommended": True
                },
                "llama-3.1-8b-instant": {
                    "name": "Llama 3.1 8B Instant", 
                    "description": "Fast and efficient - best for quick insights",
                    "context_window": 8192,
                    "recommended": False
                },
                "llama-3.1-70b-versatile": {
                    "name": "Llama 3.1 70B Versatile",
                    "description": "High-quality responses for complex tasks",
                    "context_window": 131072,
                    "recommended": True
                },
                "mixtral-8x7b-32768": {
                    "name": "Mixtral 8x7B",
                    "description": "Mixture of experts model with excellent reasoning",
                    "context_window": 32768,
                    "recommended": False
                }
            }
        },
        "openai": {
            "name": "OpenAI",
            "description": "Industry-leading AI models",
            "available": OPENAI_AVAILABLE,
            "models": {
                "gpt-4o": {
                    "name": "GPT-4o",
                    "description": "Latest GPT-4 model with vision capabilities",
                    "context_window": 128000,
                    "recommended": True
                },
                "gpt-4o-mini": {
                    "name": "GPT-4o Mini",
                    "description": "Faster and cheaper GPT-4 variant",
                    "context_window": 128000,
                    "recommended": True
                },
                "gpt-4-turbo": {
                    "name": "GPT-4 Turbo",
                    "description": "High-performance GPT-4 model",
                    "context_window": 128000,
                    "recommended": False
                },
                "gpt-3.5-turbo": {
                    "name": "GPT-3.5 Turbo",
                    "description": "Fast and cost-effective model",
                    "context_window": 16385,
                    "recommended": False
                }
            }
        },
        "anthropic": {
            "name": "Anthropic Claude",
            "description": "Advanced AI with strong reasoning capabilities",
            "available": ANTHROPIC_AVAILABLE,
            "models": {
                "claude-3-5-sonnet-20241022": {
                    "name": "Claude 3.5 Sonnet",
                    "description": "Latest Claude model with enhanced capabilities",
                    "context_window": 200000,
                    "recommended": True
                },
                "claude-3-5-haiku-20241022": {
                    "name": "Claude 3.5 Haiku",
                    "description": "Fast and efficient Claude model",
                    "context_window": 200000,
                    "recommended": True
                },
                "claude-3-opus-20240229": {
                    "name": "Claude 3 Opus",
                    "description": "Most capable Claude model",
                    "context_window": 200000,
                    "recommended": False
                },
                "claude-3-sonnet-20240229": {
                    "name": "Claude 3 Sonnet",
                    "description": "Balanced performance and speed",
                    "context_window": 200000,
                    "recommended": False
                }
            }
        }
    }
    
    DEFAULT_PROVIDER = "groq"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    
    def __init__(self, provider: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the LLM service with specified provider."""
        # Get provider from parameter, environment variable, or use default
        self.provider = provider or os.getenv("AI_PROVIDER") or self.DEFAULT_PROVIDER
        
        # Validate provider
        if self.provider not in self.PROVIDERS:
            raise ValueError(f"Invalid provider '{self.provider}'. Available: {', '.join(self.PROVIDERS.keys())}")
        
        if not self.PROVIDERS[self.provider]["available"]:
            raise ValueError(f"Provider '{self.provider}' is not available. Install required package.")
        
        # Get API key
        if self.provider == "groq":
            self.api_key = api_key or os.getenv("GROQ_API_KEY")
            if not self.api_key:
                raise ValueError("GROQ_API_KEY not found. Set it as an environment variable or pass it to the constructor.")
            self.client = Groq(api_key=self.api_key)
            
        elif self.provider == "openai":
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY not found. Set it as an environment variable or pass it to the constructor.")
            self.client = openai.OpenAI(api_key=self.api_key)
            
        elif self.provider == "anthropic":
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not found. Set it as an environment variable or pass it to the constructor.")
            self.client = anthropic.Anthropic(api_key=self.api_key)
        
        # Get model from parameter, environment variable, or use default
        self.model = model or os.getenv("AI_MODEL") or self.DEFAULT_MODEL
        
        # Validate model is available for this provider
        if self.model not in self.PROVIDERS[self.provider]["models"]:
            print(f"Warning: Model '{self.model}' not in available models list for {self.provider}. Using anyway...")
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, Dict[str, Any]]:
        """Get list of available AI providers."""
        return cls.PROVIDERS
    
    @classmethod
    def get_available_models(cls, provider: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get list of available models for a provider or all providers."""
        if provider:
            if provider not in cls.PROVIDERS:
                raise ValueError(f"Invalid provider '{provider}'")
            return cls.PROVIDERS[provider]["models"]
        
        # Return all models from all providers
        all_models = {}
        for prov, info in cls.PROVIDERS.items():
            for model_id, model_info in info["models"].items():
                all_models[f"{prov}:{model_id}"] = {
                    **model_info,
                    "provider": prov,
                    "provider_name": info["name"]
                }
        return all_models
    
    def _call_llm(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """Make a call to the configured AI provider's API."""
        try:
            system_message = "You are a FinOps expert analyzing Google Cloud Platform costs and resources. Provide clear, actionable insights and recommendations."
            
            if self.provider == "groq":
                chat_completion = self.client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": system_message
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return chat_completion.choices[0].message.content
                
            elif self.provider == "openai":
                chat_completion = self.client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": system_message
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return chat_completion.choices[0].message.content
                
            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_message,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                return response.content[0].text
                
        except Exception as e:
            return f"Error generating AI insights with {self.provider}: {str(e)}"
    
    def analyze_dashboard_data(self, data: DashboardData) -> Dict[str, Any]:
        """Generate comprehensive AI analysis of dashboard data."""
        
        # Use helper function to avoid division by zero
        change_pct = calculate_percentage_change(data.current_month_cost, data.last_month_cost)
        
        # Get top 5 services by cost
        top_services = sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Count total issues
        total_issues = sum(
            len(result.issues) for result in data.audit_results.values()
        )
        
        # Build prompt
        prompt = f"""Analyze this GCP FinOps data and provide insights:

**Cost Overview:**
- Current month: ${data.current_month_cost:,.2f}
- Last month: ${data.last_month_cost:,.2f}
- Change: {change_pct:+.1f}%
- YTD: ${data.ytd_cost:,.2f}

**Top Services by Cost:**
{chr(10).join([f"- {service}: ${cost:,.2f}" for service, cost in top_services])}

**Resource Issues:**
- Total potential savings: ${data.total_potential_savings:,.2f}/month
- Total issues found: {total_issues}

**Audit Summary:**
{chr(10).join([f"- {result.resource_type}: {result.total_count} resources, {result.untagged_count} untagged, {result.idle_count} idle" for result in data.audit_results.values() if result.total_count > 0])}

Provide your analysis in markdown format:

## Key Insights

### Cost Trends & Patterns
[3 key insights about spending patterns and trends]

### Actionable Recommendations
1. **[Priority]: [Specific recommendation]**
   [Brief explanation of impact and implementation]

2. **[Priority]: [Specific recommendation]**
   [Brief explanation of impact and implementation]

3. **[Priority]: [Specific recommendation]**
   [Brief explanation of impact and implementation]

### Critical Alerts
[Any anomalies or concerns requiring immediate attention]

Be concise but specific."""
        
        response = self._call_llm(prompt, max_tokens=800, temperature=0.6)
        
        return {
            "analysis": response,
            "provider": self.provider,
            "model_used": self.model,
            "project_id": data.project_id,
            "billing_month": data.billing_month,
        }
    
    def explain_cost_spike(self, data: DashboardData) -> str:
        """Explain why costs increased or decreased."""
        
        # Use helper function to avoid division by zero
        change_pct = calculate_percentage_change(data.current_month_cost, data.last_month_cost)
        
        if abs(change_pct) < 5:
            return "Your costs are relatively stable compared to last month (change < 5%)."
        
        direction = "increased" if change_pct > 0 else "decreased"
        top_services = sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        prompt = f"""The GCP costs {direction} by {abs(change_pct):.1f}% this month.

**Current Costs:**
- This month: ${data.current_month_cost:,.2f}
- Last month: ${data.last_month_cost:,.2f}

**Top Services:**
{chr(10).join([f"- {service}: ${cost:,.2f}" for service, cost in top_services])}

**Resource Insights:**
- Idle resources: {sum(r.idle_count for r in data.audit_results.values())}
- Untagged resources: {sum(r.untagged_count for r in data.audit_results.values())}
- Over-provisioned: {sum(r.over_provisioned_count for r in data.audit_results.values())}

Explain in 2-3 sentences why the costs {direction} and what might be causing it. Be specific and actionable."""
        
        return self._call_llm(prompt, max_tokens=300, temperature=0.5)
    
    def generate_executive_summary(self, data: DashboardData) -> str:
        """Generate an executive summary for reports."""
        
        top_services = sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True)[:3]
        
        prompt = f"""Generate a brief executive summary for this GCP FinOps report:

**Financial Overview:**
- Current month: ${data.current_month_cost:,.2f}
- YTD: ${data.ytd_cost:,.2f}
- Potential savings: ${data.total_potential_savings:,.2f}/month

**Top Services:**
{chr(10).join([f"- {service}: ${cost:,.2f}" for service, cost in top_services])}

**Optimization Opportunities:**
- {len(data.recommendations)} recommendations identified
- {sum(len(r.issues) for r in data.audit_results.values())} total issues

Format your response in markdown:

## Executive Summary

[Write a professional 3-4 sentence summary suitable for executives. Focus on business impact and key takeaways. Include specific dollar amounts and percentages where relevant.]

### Key Metrics
- **Current Monthly Spend:** ${data.current_month_cost:,.2f}
- **Potential Monthly Savings:** ${data.total_potential_savings:,.2f}
- **Optimization Opportunities:** {len(data.recommendations)} recommendations

### Next Steps
[Brief 1-2 sentence recommendation on immediate actions executives should take.]"""
        
        return self._call_llm(prompt, max_tokens=250, temperature=0.6)
    
    def answer_question(self, question: str, data: DashboardData, context: Optional[str] = None) -> str:
        """Answer a natural language question about the FinOps data."""
        
        # Build detailed context from dashboard data
        base_context = f"""You have access to the following GCP FinOps data:

**Costs:**
- Current month: ${data.current_month_cost:,.2f}
- Last month: ${data.last_month_cost:,.2f}
- YTD: ${data.ytd_cost:,.2f}

**Service Costs:**
{chr(10).join([f"- {service}: ${cost:,.2f}" for service, cost in sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True)])}

**Detailed Resource Information:**
{self._format_detailed_resources(data)}

**Optimization Recommendations:**
{self._format_recommendations(data)}

**Potential Savings:** ${data.total_potential_savings:,.2f}/month

**Question:** {question}

Provide a clear, specific answer based on the detailed data above. Use the specific resource names, costs, and recommendations when available."""
        
        # Add additional context if provided (e.g., conversation history)
        if context:
            full_context = f"{base_context}\n\n{context}"
        else:
            full_context = base_context
        
        return self._call_llm(full_context, max_tokens=500, temperature=0.5)
    
    def _format_detailed_resources(self, data: DashboardData) -> str:
        """Format detailed resource information for AI context."""
        if not data.audit_results:
            return "No detailed resource information available."
        
        formatted_resources = []
        for resource_type, result in data.audit_results.items():
            if result.total_count > 0:
                resource_info = f"**{result.resource_type.replace('_', ' ').title()}:**\n"
                resource_info += f"  - Total: {result.total_count}\n"
                resource_info += f"  - Idle: {result.idle_count}\n"
                resource_info += f"  - Untagged: {result.untagged_count}\n"
                resource_info += f"  - Over-provisioned: {result.over_provisioned_count}\n"
                resource_info += f"  - Potential monthly savings: ${result.potential_monthly_savings:,.2f}\n"
                
                if result.issues:
                    resource_info += f"  - Issues: {', '.join(result.issues)}\n"
                
                formatted_resources.append(resource_info)
        
        return "\n".join(formatted_resources) if formatted_resources else "No resources found."
    
    def _format_recommendations(self, data: DashboardData) -> str:
        """Format optimization recommendations for AI context."""
        if not data.recommendations:
            return "No specific recommendations available."
        
        formatted_recs = []
        for i, rec in enumerate(data.recommendations[:10], 1):  # Limit to top 10
            rec_info = f"{i}. **{rec.resource_type.replace('_', ' ').title()} - {rec.resource_name}**\n"
            rec_info += f"   - Region: {rec.region}\n"
            rec_info += f"   - Issue: {rec.issue}\n"
            rec_info += f"   - Recommendation: {rec.recommendation}\n"
            rec_info += f"   - Potential savings: ${rec.potential_monthly_savings:,.2f}/month\n"
            rec_info += f"   - Priority: {rec.priority}\n"
            if rec.details:
                rec_info += f"   - Details: {rec.details}\n"
            formatted_recs.append(rec_info)
        
        return "\n".join(formatted_recs)
    
    def prioritize_recommendations(self, recommendations: List[OptimizationRecommendation]) -> str:
        """Help prioritize which recommendations to act on first."""
        
        if not recommendations:
            return "No recommendations available to prioritize."
        
        # Get top 10 by savings
        top_recs = sorted(recommendations, key=lambda x: x.potential_monthly_savings, reverse=True)[:10]
        
        rec_list = "\n".join([
            f"- {rec.resource_type} '{rec.resource_name}': {rec.issue} (Savings: ${rec.potential_monthly_savings:,.2f}/mo, Priority: {rec.priority})"
            for rec in top_recs
        ])
        
        prompt = f"""Given these optimization recommendations, suggest which 3 should be prioritized and why:

{rec_list}

Consider:
1. Savings potential
2. Implementation difficulty
3. Business risk

Provide your response in the following markdown format:

## Here are the top 3 optimization recommendations to prioritize:

1. **[Resource Name]: [Brief Issue Description] (Savings: $X.XX/mo, Priority: [level])**
   [Detailed explanation of why this should be prioritized, including implementation difficulty and business risk assessment.]

2. **[Resource Name]: [Brief Issue Description] (Savings: $X.XX/mo, Priority: [level])**
   [Detailed explanation of why this should be prioritized, including implementation difficulty and business risk assessment.]

3. **[Resource Name]: [Brief Issue Description] (Savings: $X.XX/mo, Priority: [level])**
   [Detailed explanation of why this should be prioritized, including implementation difficulty and business risk assessment.]

[Concluding paragraph summarizing the overall prioritization strategy and expected outcomes.]"""
        
        return self._call_llm(prompt, max_tokens=500, temperature=0.6)
    
    def suggest_budget_alerts(self, data: DashboardData) -> str:
        """Suggest appropriate budget alerts based on spending patterns."""
        
        avg_monthly = data.ytd_cost / 10  # Approximate average
        
        prompt = f"""Based on this GCP spending pattern, suggest appropriate budget alerts:

**Current Costs:**
- This month: ${data.current_month_cost:,.2f}
- Average monthly (estimated): ${avg_monthly:,.2f}
- YTD: ${data.ytd_cost:,.2f}

**Top Services:**
{chr(10).join([f"- {service}: ${cost:,.2f}" for service, cost in sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True)[:5]])}

Suggest:
1. Overall monthly budget threshold
2. Alert percentage (e.g., 80% of budget)
3. Any service-specific budgets
4. Threshold for anomaly detection

Be specific with dollar amounts."""
        
        return self._call_llm(prompt, max_tokens=400, temperature=0.6)
    
    def analyze_resource_utilization(self, audit_results: Dict[str, AuditResult]) -> str:
        """Analyze resource utilization patterns."""
        
        if not audit_results:
            return "No audit data available."
        
        summary = "\n".join([
            f"- {result.resource_type}: {result.total_count} total, {result.idle_count} idle ({result.idle_count/result.total_count*100:.1f}% idle)" if result.total_count > 0 else f"- {result.resource_type}: No resources"
            for result in audit_results.values()
        ])
        
        prompt = f"""Analyze these resource utilization patterns:

{summary}

Total potential savings from optimization: ${sum(r.potential_monthly_savings for r in audit_results.values()):,.2f}/month

Provide:
1. Overall utilization assessment
2. Which resource types need immediate attention
3. Pattern observations (e.g., many idle resources might indicate over-provisioning)"""
        
        return self._call_llm(prompt, max_tokens=500, temperature=0.6)


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> Optional[LLMService]:
    """Get or create LLM service singleton."""
    global _llm_service
    
    if _llm_service is None:
        try:
            _llm_service = LLMService()
        except ValueError:
            # API key not configured
            return None
    
    return _llm_service


def refresh_llm_service() -> Optional[LLMService]:
    """Refresh the LLM service singleton with current environment variables."""
    global _llm_service
    
    # Reset the singleton to force recreation
    _llm_service = None
    
    # Create new instance with current environment
    try:
        _llm_service = LLMService()
        return _llm_service
    except ValueError:
        # API key not configured
        return None

