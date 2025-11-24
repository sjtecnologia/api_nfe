"""
🎓 Script de Treinamento - LLM NCM com Lei Complementar 214/2025
Treina Llama-3.1-8B para classificação tributária com embasamento legal
"""

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig
)
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import json
import os
from datetime import datetime

# ==================== CONFIGURAÇÕES ====================

CONFIG = {
    # Modelo base (ajuste conforme sua instalação)
    "model_name": "meta-llama/Llama-3.1-8B-Instruct",  # ou caminho local
    
    # Caminhos
    "dataset_file": "dataset_treinamento_ncm_lc214_2025.jsonl",
    "output_dir": "./models/llm_ncm_lc214_trained",
    "logs_dir": "./logs/training",
    
    # Hiperparâmetros de treinamento
    "num_epochs": 3,
    "batch_size": 2,
    "gradient_accumulation_steps": 4,
    "learning_rate": 2e-5,
    "max_seq_length": 1024,
    
    # LoRA (Low-Rank Adaptation)
    "lora_r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    
    # Outros
    "seed": 42,
    "use_8bit": True,  # Quantização 8-bit para economizar memória
}

# ==================== FUNÇÕES AUXILIARES ====================

def print_header(text: str):
    """Imprime cabeçalho formatado"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")

def check_gpu():
    """Verifica disponibilidade de GPU"""
    if torch.cuda.is_available():
        print(f"✅ GPU disponível: {torch.cuda.get_device_name(0)}")
        print(f"   Memória: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        return True
    else:
        print("⚠️ GPU não disponível - usando CPU (será muito mais lento)")
        return False

def load_and_prepare_model(config):
    """Carrega e prepara o modelo para treinamento"""
    print_header("🔄 Carregando Modelo Base")
    
    # Configuração de quantização
    if config["use_8bit"]:
        bnb_config = BitsAndBytesConfig(
            load_in_8bit=True,
            bnb_8bit_compute_dtype=torch.float16,
            bnb_8bit_use_double_quant=True,
        )
    else:
        bnb_config = None
    
    # Carregar tokenizer
    print("📝 Carregando tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(config["model_name"])
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    
    # Carregar modelo
    print("🤖 Carregando modelo...")
    model = AutoModelForCausalLM.from_pretrained(
        config["model_name"],
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True
    )
    
    # Configurar LoRA
    print("⚙️ Configurando LoRA (Low-Rank Adaptation)...")
    lora_config = LoraConfig(
        r=config["lora_r"],
        lora_alpha=config["lora_alpha"],
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=config["lora_dropout"],
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_config)
    
    # Imprimir parâmetros treináveis
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"📊 Parâmetros treináveis: {trainable_params:,} ({100 * trainable_params / total_params:.2f}%)")
    
    return model, tokenizer

def load_and_process_dataset(config, tokenizer):
    """Carrega e processa o dataset de treinamento"""
    print_header("📚 Carregando Dataset")
    
    if not os.path.exists(config["dataset_file"]):
        raise FileNotFoundError(f"Dataset não encontrado: {config['dataset_file']}")
    
    # Carregar dataset
    print(f"📁 Lendo arquivo: {config['dataset_file']}")
    dataset = load_dataset("json", data_files=config["dataset_file"])
    
    print(f"✅ {len(dataset['train'])} exemplos carregados")
    
    # Função de formatação
    def format_example(example):
        """Formata exemplo no formato de chat do Llama"""
        messages = example["messages"]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False
        )
        return {"text": text}
    
    # Processar dataset
    print("🔄 Processando exemplos...")
    processed_dataset = dataset.map(
        format_example,
        remove_columns=dataset["train"].column_names
    )
    
    # Tokenizar
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=config["max_seq_length"],
            padding="max_length"
        )
    
    print("🔤 Tokenizando...")
    tokenized_dataset = processed_dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=["text"]
    )
    
    return tokenized_dataset["train"]

def setup_training_args(config):
    """Configura argumentos de treinamento"""
    print_header("⚙️ Configurando Treinamento")
    
    # Criar diretórios
    os.makedirs(config["output_dir"], exist_ok=True)
    os.makedirs(config["logs_dir"], exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"ncm_lc214_{timestamp}"
    
    training_args = TrainingArguments(
        output_dir=config["output_dir"],
        num_train_epochs=config["num_epochs"],
        per_device_train_batch_size=config["batch_size"],
        gradient_accumulation_steps=config["gradient_accumulation_steps"],
        learning_rate=config["learning_rate"],
        logging_dir=config["logs_dir"],
        logging_steps=5,
        save_steps=50,
        save_total_limit=3,
        warmup_steps=10,
        fp16=True,
        optim="paged_adamw_8bit",
        report_to="none",  # Desabilita W&B, TensorBoard, etc.
        run_name=run_name,
        seed=config["seed"],
        data_seed=config["seed"],
    )
    
    print(f"📊 Configuração:")
    print(f"   - Épocas: {config['num_epochs']}")
    print(f"   - Batch size: {config['batch_size']}")
    print(f"   - Learning rate: {config['learning_rate']}")
    print(f"   - LoRA rank: {config['lora_r']}")
    print(f"   - Diretório de saída: {config['output_dir']}")
    
    return training_args

def train_model(model, tokenizer, train_dataset, training_args):
    """Executa o treinamento"""
    print_header("🎓 Iniciando Treinamento")
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        tokenizer=tokenizer,
    )
    
    # Treinar
    print("🚀 Treinando modelo...")
    start_time = datetime.now()
    
    try:
        trainer.train()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ Treinamento concluído em {duration/60:.1f} minutos!")
        
        return trainer
        
    except KeyboardInterrupt:
        print("\n⚠️ Treinamento interrompido pelo usuário")
        return None
    except Exception as e:
        print(f"\n❌ Erro durante treinamento: {e}")
        raise

def save_model(model, tokenizer, config):
    """Salva o modelo treinado"""
    print_header("💾 Salvando Modelo")
    
    # Salvar modelo
    print(f"📁 Salvando em: {config['output_dir']}")
    model.save_pretrained(config["output_dir"])
    tokenizer.save_pretrained(config["output_dir"])
    
    # Salvar configuração
    config_path = os.path.join(config["output_dir"], "training_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("✅ Modelo salvo com sucesso!")
    print(f"\n📝 Para usar o modelo no LM Studio:")
    print(f"   1. Copie a pasta: {config['output_dir']}")
    print(f"   2. Carregue no LM Studio como modelo local")
    print(f"   3. Inicie o servidor na porta 1234")

def test_model(model, tokenizer):
    """Testa o modelo treinado"""
    print_header("🧪 Testando Modelo")
    
    test_prompt = """Produto: Café torrado em grãos

Dados NCM disponíveis:
**NCM 09.01.21.10** - Café torrado, não descafeinado, em grão

Classifique este produto fornecendo NCM, CFOP, CST/CSOSN, CEST e embasamento legal da LC 214/2025."""
    
    messages = [
        {
            "role": "system",
            "content": "Você é um especialista em classificação tributária NCM com conhecimento da LC 214/2025."
        },
        {
            "role": "user",
            "content": test_prompt
        }
    ]
    
    # Preparar input
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    
    # Gerar resposta
    print("🤖 Gerando resposta de teste...")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.1,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    
    print("\n📋 Resposta do modelo:")
    print("-" * 60)
    print(response)
    print("-" * 60)

# ==================== FUNÇÃO PRINCIPAL ====================

def main():
    """Função principal de treinamento"""
    print_header("🎓 Treinamento LLM - NCM com LC 214/2025")
    
    # Verificar GPU
    has_gpu = check_gpu()
    if not has_gpu:
        print("\n⚠️ ATENÇÃO: Treinamento sem GPU será MUITO lento!")
        response = input("Deseja continuar mesmo assim? (s/n): ")
        if response.lower() != 's':
            print("❌ Treinamento cancelado")
            return
    
    try:
        # 1. Carregar modelo
        model, tokenizer = load_and_prepare_model(CONFIG)
        
        # 2. Carregar dataset
        train_dataset = load_and_process_dataset(CONFIG, tokenizer)
        
        # 3. Configurar treinamento
        training_args = setup_training_args(CONFIG)
        
        # 4. Treinar
        trainer = train_model(model, tokenizer, train_dataset, training_args)
        
        if trainer is None:
            return
        
        # 5. Salvar
        save_model(model, tokenizer, CONFIG)
        
        # 6. Testar
        test_model(model, tokenizer)
        
        print_header("✅ Processo Concluído com Sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
