# PromptCraft CLI

A powerful command-line interface for crafting high-quality, structured, and context-rich prompts for Large Language Models (LLMs).

## What is This?

PromptCraft helps engineers move from simple "prompting" to detailed "specifying." It offers both lightning-fast one-liner commands for common tasks and a comprehensive interactive builder for complex prompts. The tool intelligently analyzes your code, extracts relevant context, and generates perfectly formatted prompts for better LLM interactions.

## ⚡ Key Features

### 🚀 **Quick Mode Commands** (NEW!)
- **Instant Code Reviews**: `promptcraft review main.py` - Get code review prompts in seconds
- **Smart Debugging**: `promptcraft debug "error message"` - Generate debugging assistance
- **Code Explanations**: `promptcraft explain complex_file.js` - Create educational prompts
- **Test Generation**: `promptcraft test calculator.py` - Build comprehensive test prompts
- **Custom Templates**: `promptcraft quick --template=refactoring --file=legacy.py`

### 🧠 **Smart Context Extraction**
- **Python Files**: Automatically extracts imports, functions, classes, and coding patterns
- **JavaScript/React**: Detects imports, components, hooks, and project dependencies  
- **Multi-Language**: Supports Python, JS/TS, Java, Go, Rust, C++, Ruby, PHP
- **Intelligent Analysis**: Identifies async patterns, test code, frameworks, and more

### 📚 **Template Library**
- **Pre-built Templates**: code-review, debugging, feature-planning, refactoring, testing
- **Project Detection**: Automatically suggests relevant templates based on your codebase
- **Template Management**: `promptcraft template list/show/use` commands

### 🎯 **Interactive Builder**
- **Guided Interface**: Step-by-step prompt construction
- **File Integration**: Browse and include files with `@filename` syntax
- **Session Management**: Save, load, and reuse complex prompts
- **Direct LLM Execution**: Run prompts against OpenAI API with rich formatting

## Installation

This project is managed with Poetry.

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd promptcraft-cli
    ```

2.  **Install dependencies using Poetry:**
    ```bash
    poetry install
    ```

3.  **Set your OpenAI API Key:**
    The `run` command requires access to the OpenAI API. Set your key as an environment variable.
    ```bash
    export OPENAI_API_KEY='your-secret-api-key'
    ```
    *Tip: Add this line to your shell's configuration file (`.zshrc`, `.bashrc`) to make it permanent.*

## 🚀 Quick Start

### ⚡ **Fast Track** (Most Common Use Cases)

```bash
# 1. Install dependencies
poetry install

# 2. Instant code review (copies prompt to clipboard)
poetry run promptcraft review src/main.py

# 3. Debug an error
poetry run promptcraft debug "ImportError: No module named requests"

# 4. Explain complex code
poetry run promptcraft explain algorithm.py

# 5. Generate test cases
poetry run promptcraft test calculator.py
```

**That's it!** 🎉 Your intelligent prompts are copied to clipboard, ready to paste into ChatGPT, Claude, or any LLM.

### 🎯 **Full Setup** (For Advanced Features)

1.  **Initialize Project Configuration:**
    ```bash
    poetry run promptcraft init
    ```
    Creates `.promptcraft.yml` with your tech stack details for smarter suggestions.

2.  **Explore Templates:**
    ```bash
    poetry run promptcraft template list          # See all templates
    poetry run promptcraft template show debugging # View template details
    poetry run promptcraft template use refactoring # Load and customize
    ```

3.  **Interactive Builder** (For Complex Prompts):
    ```bash
    poetry run promptcraft
    ```
    Opens the guided menu for detailed prompt construction.

4.  **Session Management:**
    ```bash
    poetry run promptcraft list                    # View saved sessions  
    poetry run promptcraft load my-session         # Reload and edit
    poetry run promptcraft run my-session          # Execute with LLM
    ```

### 🔧 **Optional: LLM Integration**
Set up direct LLM execution (optional):
```bash
export OPENAI_API_KEY='your-secret-api-key'
poetry run promptcraft run my-session  # Streams response with syntax highlighting
```

## 💡 Usage Examples

### **Quick Code Review Workflow**
```bash
# While coding, get instant feedback
poetry run promptcraft review current_file.py
# → Copies comprehensive review prompt to clipboard
# → Paste into your favorite LLM for instant feedback!
```

### **Debugging Workflow** 
```bash
# Hit an error? Get debugging help instantly
poetry run promptcraft debug "TypeError: list indices must be integers"
# → Generates debugging prompt with error analysis
# → Paste into LLM for step-by-step debugging guide
```

### **Learning Workflow**
```bash
# Understanding complex code
poetry run promptcraft explain react_component.jsx
# → Creates educational prompt with smart React context
# → Get detailed explanations of hooks, components, patterns
```

### **Custom Template Workflow**
```bash
# Use specific templates with your files
poetry run promptcraft quick --template=refactoring --file=legacy_code.py
poetry run promptcraft quick --template=feature-planning --file=requirements.md

# Preview before copying
poetry run promptcraft quick --template=testing --file=utils.py --output
```

## 📖 Command Reference

### **🚀 Quick Commands** (Most Used)

| Command | Description | Example |
|---------|-------------|---------|
| `review <file>` | Instant code review | `promptcraft review main.py` |
| `debug "<error>"` | Debug error messages | `promptcraft debug "NameError: undefined"` |
| `explain <file>` | Code explanation | `promptcraft explain algorithm.js` |
| `test <file>` | Generate test cases | `promptcraft test calculator.py` |

### **⚙️ Base Quick Command**

```bash
promptcraft quick [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--template` | Template to use | `code-review` |
| `--file` | File to include in context | None |
| `--output` | Show output instead of clipboard | `False` |

**Examples:**
```bash
promptcraft quick --template=debugging --file=app.py
promptcraft quick --template=refactoring --file=legacy.js --output
```

### **📚 Template Management**

| Command | Description |
|---------|-------------|
| `template list` | Show all available templates |
| `template show <name>` | View template details |
| `template use <name>` | Load template into interactive mode |

### **🎯 Interactive & Sessions**

| Command | Description |
|---------|-------------|
| `promptcraft` | Start interactive prompt builder |
| `init` | Initialize project configuration |
| `list` | Show saved sessions |
| `load <name>` | Load and edit a session |
| `run <name>` | Execute session with LLM |

### **🧠 Smart Context Features**

PromptCraft automatically detects and extracts:

#### **Python Files** 
- ✅ Imports (`import pandas`, `from django import`)
- ✅ Function & class definitions  
- ✅ Async patterns, main blocks, test indicators

#### **JavaScript/TypeScript/React**
- ✅ Imports & exports (`import React`, `export default`)
- ✅ Functions (`const handleClick = () =>`, `function getData()`)
- ✅ React patterns (hooks, components, JSX)
- ✅ Package.json dependencies

#### **Other Languages**
- ✅ Java, Go, Rust, C++, Ruby, PHP support
- ✅ Falls back to basic content for unknown types

## 🎯 Pro Tips

### **Speed Up Your Workflow**
```bash
# Create shell aliases for super-fast access
alias pcr="poetry run promptcraft review"
alias pcd="poetry run promptcraft debug" 
alias pce="poetry run promptcraft explain"

# Now just use:
pcr main.py        # Instant code review
pcd "syntax error" # Quick debugging
pce complex.js     # Code explanation
```

### **Integration with LLMs**
1. Run any quick command (copies to clipboard)
2. Paste directly into:
   - ChatGPT
   - Claude
   - Gemini
   - Local LLMs
3. Get intelligent, context-aware responses!

### **Project-Specific Templates**
```bash
# Initialize project config for smart suggestions
promptcraft init

# PromptCraft will auto-suggest relevant templates based on:
# - Detected frameworks (React, Django, FastAPI)
# - File types in your project
# - Existing dependencies
```
