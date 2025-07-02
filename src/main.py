#!/usr/bin/env python3

import os
import sys
import signal
import time
import logging
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from dotenv import load_dotenv

# Import from relative paths for container environment
try:
    from .config import config
    from .ai.openrouter_client import OpenRouterClient
    from .database.database import RealEstateDatabase
    from .query.router import QueryRouter
    from .core.chat_agent import ChatAgent
except ImportError:
    # Fallback for direct execution
    from config import config
    from ai.openrouter_client import OpenRouterClient
    from database.database import RealEstateDatabase
    from query.router import QueryRouter
    from core.chat_agent import ChatAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.app.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Rich console
console = Console()

def signal_handler(sig, frame):
    """Handle graceful shutdown"""
    console.print("\n\n👋 Thank you for using Real Estate Market Insights Chat Agent!")
    console.print("Goodbye!")
    sys.exit(0)

def print_banner():
    """Print application banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                     🏠 Real Estate Market Insights Chat Agent                 ║
║                                                                              ║
║                       🤖 AI-Powered Property Analysis                        ║
║                         💬 Powered by OpenRouter                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="cyan", justify="center")

def show_help():
    """Display help information"""
    help_text = """
📋 Available Commands:
────────────────────────────────────────────────────────────────────────────────

💬 Chat Commands:
  help        - Show this help message
  examples    - Show example queries
  clear       - Clear the screen
  exit/quit   - Exit the application
  status      - Show API usage and rate limits
  models      - List available OpenRouter models

🏠 Analysis Types:
  Market Yield       - Calculate gross yield for properties
  Market Trends      - Analyze price and rent trends
  Area Comparison    - Compare two areas side-by-side
  Price Discovery    - Find average price per square foot

💡 Tips:
  • Use natural language to ask questions
  • Be specific about location and property type
  • Ask follow-up questions for deeper analysis
────────────────────────────────────────────────────────────────────────────────
    """
    console.print(help_text)

def show_examples():
    """Display example queries"""
    examples = """
📋 Example Queries:
────────────────────────────────────────────────────────────────────────────────

🏠 Market Yield Examples:
  "What's the rental yield for 2-bedroom apartments in Seattle?"
  "Show me gross yield for studios in downtown Manhattan"
  "Calculate yield for single-family homes in Austin"

📈 Market Trends Examples:
  "What are the price trends for Seattle over the last year?"
  "Show me rental trends in San Francisco"
  "How has the Portland market performed this quarter?"

🔍 Area Comparison Examples:
  "Compare Seattle vs Portland for rental investment"
  "Which is better for yield: Brooklyn or Queens?"
  "Compare downtown vs suburbs in Chicago"

💰 Price Discovery Examples:
  "What's the average price per square foot in Miami?"
  "Show me price trends for condos in Boston"
  "What do 3-bedroom houses cost in Denver?"
────────────────────────────────────────────────────────────────────────────────
    """
    console.print(examples)

class RealEstateChatAgent:
    """Main chat agent application"""
    
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.router = QueryRouter()
        self.ai_client = OpenRouterClient()
        self.db = RealEstateDatabase()
        self.session_queries = 0
        self.session_start = time.time()
        
    def display_status(self):
        """Display current status and usage"""
        # Get rate limit info
        rate_info = self.ai_client.check_rate_limits()
        
        # Session info
        session_duration = time.time() - self.session_start
        
        status_table = Table(title="Session Status", show_header=True, header_style="bold yellow")
        status_table.add_column("Metric", style="yellow", width=30)
        status_table.add_column("Value", style="white")
        
        status_data = [
            ("Session Duration", f"{session_duration/60:.1f} minutes"),
            ("Queries in Session", str(self.session_queries)),
            ("Daily API Limit", str(rate_info['daily_limit'])),
            ("API Calls Used Today", str(rate_info['current_usage'])),
            ("Remaining API Calls", str(rate_info['remaining_calls'])),
            ("Usage Percentage", f"{rate_info['usage_percentage']:.1f}%"),
            ("Current Model", config.openrouter.default_model),
            ("Database Connected", "Yes" if self.db.test_connection() else "No")
        ]
        
        for metric, value in status_data:
            status_table.add_row(metric, value)
        
        console.print(status_table)
        console.print()
    
    def display_models(self):
        """Display available models"""
        models = self.ai_client.get_available_models()
        
        models_table = Table(title="Available OpenRouter Models", show_header=True, header_style="bold magenta")
        models_table.add_column("Model", style="magenta", width=50)
        models_table.add_column("Type", style="white")
        
        for model in models:
            model_type = "Free" if ":free" in model else "Paid"
            models_table.add_row(model, model_type)
        
        console.print(models_table)
        console.print()
    
    def process_query(self, query: str):
        """Process a user query"""
        self.session_queries += 1
        
        # Show processing indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(description="Analyzing query...", total=None)
            
            try:
                # Route and process the query
                response = self.router.route_query(query)
                progress.update(task, description="Generating response...")
                
            except Exception as e:
                console.print(f"[red]Error processing query: {str(e)}[/red]")
                logger.error(f"Query processing error: {str(e)}")
                return None
        
        # Display response
        self._display_response(response, query)
        return response
    
    def _display_response(self, response, original_query):
        """Display formatted response"""
        # Parse query type for appropriate formatting
        parsed = self.router.parse_query(original_query)
        
        # Create response panel based on query type
        if "yield" in original_query.lower():
            title = "📊 Market Yield Analysis"
            border_color = "green"
        elif "trend" in original_query.lower():
            title = "📈 Market Trends"
            border_color = "blue"
        elif "compar" in original_query.lower():
            title = "🔍 Location Comparison"
            border_color = "yellow"
        elif "investment" in original_query.lower():
            title = "💰 Investment Opportunities"
            border_color = "gold1"
        elif "summary" in original_query.lower():
            title = "📋 Market Summary"
            border_color = "cyan"
        else:
            title = "🏠 Market Insights"
            border_color = "white"
        
        console.print(f"\n💬 {response.content}")
        console.print(f"⏱ Response time: {response.response_time:.2f}s")
        console.print(f"🤖 Model used: {response.model_used}")
        console.print(f"🔧 Engine: {response.engine_used}\n")
    
    def run(self):
        """Run the interactive chat interface"""
        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print_banner()
        
        # Test connections
        with console.status("Testing connections..."):
            if not self.ai_client.test_connection():
                console.print("[red]⚠️  Warning: OpenRouter connection test failed![/red]")
                console.print("[yellow]Please check your OPENROUTER_API_KEY in .env file[/yellow]")
            
            if not self.db.test_connection():
                console.print("[yellow]⚠️  Warning: Database connection test failed![/yellow]")
                console.print("[dim]The agent will work with limited functionality using AI-only responses.[/dim]")
        
        console.print("\n🏠 Welcome to Real Estate Market Insights Chat Agent!")
        console.print("💬 Type 'help' for commands, 'examples' for sample queries, or 'exit' to quit.\n")
        
        # Main interaction loop
        while True:
            try:
                # Get user input - handle both TTY and non-TTY environments
                try:
                    query = console.input("🤖 Chat Agent > ").strip()
                except EOFError:
                    # Handle non-TTY environment
                    console.print("[yellow]Non-interactive environment detected. Reading from stdin...[/yellow]")
                    query = input().strip() if sys.stdin.isatty() else sys.stdin.readline().strip()
                
                if not query:
                    continue
                
                # Handle commands
                if query.lower() in ['exit', 'quit', 'bye']:
                    signal_handler(None, None)
                elif query.lower() == 'help':
                    show_help()
                elif query.lower() == 'examples':
                    show_examples()
                elif query.lower() == 'status':
                    self.display_status()
                elif query.lower() == 'models':
                    self.display_models()
                elif query.lower() == 'clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
                    print_banner()
                else:
                    # Process as a real estate query
                    console.print("🔍 Analyzing your request...")
                    self.process_query(query)
                    
            except KeyboardInterrupt:
                signal_handler(None, None)
            except Exception as e:
                console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
                logger.error(f"Unexpected error in main loop: {str(e)}")

@click.command()
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--test-mode', is_flag=True, help='Run in test mode')
def main(debug: bool, test_mode: bool):
    """Real Estate Market Insights Chat Agent - CLI Interface"""
    
    # Setup logging level
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    try:
        # Validate configuration
        config.validate()
        
        # Initialize and run chat agent
        agent = RealEstateChatAgent(test_mode=test_mode)
        agent.run()
        
    except ValueError as e:
        console.print(f"[red]Configuration error: {str(e)}[/red]")
        console.print("[yellow]Please check your .env file and ensure all required values are set.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Fatal error: {str(e)}[/red]")
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()