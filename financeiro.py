"""
TRIMONEY - Gerenciador Financeiro Pessoal
Módulo de lógica de negócio (mobile version)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class StatusDespesa(str, Enum):
    PENDENTE = "Pendente"
    PAGA = "Paga"

class CategoriaDespesa(str, Enum):
    FIXA = "Fixa"
    VARIAVEL = "Variável"

@dataclass
class Despesa:
    id: int
    nome: str
    valor: float
    vencimento: datetime
    categoria: CategoriaDespesa
    status: StatusDespesa
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para serialização"""
        return {
            'id': self.id,
            'nome': self.nome,
            'valor': self.valor,
            'vencimento': self.vencimento.strftime("%Y-%m-%d"),
            'categoria': self.categoria.value,
            'status': self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Despesa':
        """Cria Despesa a partir de dicionário"""
        return cls(
            id=data['id'],
            nome=data['nome'],
            valor=data['valor'],
            vencimento=datetime.strptime(data['vencimento'], "%Y-%m-%d"),
            categoria=CategoriaDespesa(data['categoria']),
            status=StatusDespesa(data['status'])
        )

class GerenciadorFinanceiro:
    def __init__(self, data_dir: Optional[str] = None):
        """Inicializa o gerenciador financeiro"""
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            # Para Android, usar diretório de documentos
            if sys.platform == 'linux' and 'ANDROID_ARGUMENT' in os.environ:
                from android.storage import app_storage_path
                self.data_dir = Path(app_storage_path())
            else:
                self.data_dir = Path.home() / "trimoney"
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "trimoney_data.json"
        
        self.saldo: float = 0.0
        self.data_saldo: Optional[str] = None
        self.despesas: List[Despesa] = []
        self.proximo_id: int = 1
        
        self.carregar_dados()
    
    def carregar_dados(self) -> None:
        """Carrega dados do arquivo JSON"""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                
                self.saldo = dados.get('saldo', 0.0)
                self.data_saldo = dados.get('data_saldo')
                
                # Carregar despesas
                self.despesas = []
                for despesa_data in dados.get('despesas', []):
                    self.despesas.append(Despesa.from_dict(despesa_data))
                
                # Encontrar próximo ID
                if self.despesas:
                    self.proximo_id = max(d['id'] for d in dados['despesas']) + 1
                    
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
            self.despesas = []
            self.saldo = 0.0
            self.proximo_id = 1
    
    def salvar_dados(self) -> None:
        """Salva dados no arquivo JSON"""
        try:
            dados = {
                'saldo': self.saldo,
                'data_saldo': self.data_saldo or datetime.now().strftime("%Y-%m-%d"),
                'despesas': [despesa.to_dict() for despesa in self.despesas]
            }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Erro ao salvar dados: {e}")
            raise
    
    def definir_saldo(self, novo_saldo: float) -> None:
        """Define novo saldo"""
        self.saldo = novo_saldo
        self.data_saldo = datetime.now().strftime("%Y-%m-%d")
        self.salvar_dados()
    
    def adicionar_saldo(self, valor: float) -> None:
        """Adiciona valor ao saldo atual"""
        self.saldo += valor
        self.data_saldo = datetime.now().strftime("%Y-%m-%d")
        self.salvar_dados()
    
    def adicionar_despesa(self, nome: str, valor: float, 
                         vencimento: datetime, 
                         categoria: CategoriaDespesa) -> Despesa:
        """Adiciona uma nova despesa"""
        nova_despesa = Despesa(
            id=self.proximo_id,
            nome=nome,
            valor=valor,
            vencimento=vencimento,
            categoria=categoria,
            status=StatusDespesa.PENDENTE
        )
        
        self.despesas.append(nova_despesa)
        self.proximo_id += 1
        self.salvar_dados()
        
        return nova_despesa
    
    def marcar_despesa_como_paga(self, id_despesa: int) -> bool:
        """Marca uma despesa como paga"""
        for despesa in self.despesas:
            if despesa.id == id_despesa and despesa.status == StatusDespesa.PENDENTE:
                if self.saldo >= despesa.valor:
                    despesa.status = StatusDespesa.PAGA
                    self.saldo -= despesa.valor
                    self.salvar_dados()
                    return True
                else:
                    raise ValueError(f"Saldo insuficiente. Saldo atual: R$ {self.saldo:.2f}, "
                                   f"Valor necessário: R$ {despesa.valor:.2f}")
        return False
    
    def excluir_despesa(self, id_despesa: int) -> None:
        """Exclui uma despesa"""
        self.despesas = [d for d in self.despesas if d.id != id_despesa]
        self.salvar_dados()
    
    def calcular_resumo(self) -> Dict[str, float]:
        """Calcula resumo financeiro"""
        hoje = datetime.now()
        
        total_gasto = sum(
            d.valor for d in self.despesas 
            if d.status == StatusDespesa.PAGA
        )
        
        total_pendente = sum(
            d.valor for d in self.despesas 
            if d.status == StatusDespesa.PENDENTE
        )
        
        # Despesas vencidas
        despesas_vencidas = [
            d for d in self.despesas 
            if d.status == StatusDespesa.PENDENTE and d.vencimento < hoje
        ]
        
        total_vencidas = sum(d.valor for d in despesas_vencidas)
        
        # Despesas próximas do vencimento (3 dias)
        tres_dias = hoje.replace(hour=23, minute=59, second=59) + timedelta(days=3)
        despesas_proximas = [
            d for d in self.despesas 
            if d.status == StatusDespesa.PENDENTE and 
            hoje < d.vencimento <= tres_dias
        ]
        
        total_proximas = sum(d.valor for d in despesas_proximas)
        
        return {
            'saldo_atual': self.saldo,
            'total_gasto': total_gasto,
            'total_pendente': total_pendente,
            'saldo_final': self.saldo - total_pendente,
            'total_vencidas': total_vencidas,
            'total_proximas': total_proximas,
            'num_vencidas': len(despesas_vencidas),
            'num_proximas': len(despesas_proximas)
        }
    
    def filtrar_despesas(self, filtro: str = "todas") -> List[Despesa]:
        """Filtra despesas com base no status"""
        hoje = datetime.now()
        
        if filtro == "todas":
            return self.despesas.copy()
        elif filtro == "pendentes":
            return [d for d in self.despesas if d.status == StatusDespesa.PENDENTE]
        elif filtro == "pagas":
            return [d for d in self.despesas if d.status == StatusDespesa.PAGA]
        elif filtro == "vencidas":
            return [d for d in self.despesas 
                   if d.status == StatusDespesa.PENDENTE and d.vencimento < hoje]
        elif filtro == "proximas":
            tres_dias = hoje.replace(hour=23, minute=59, second=59) + timedelta(days=3)
            return [d for d in self.despesas 
                   if d.status == StatusDespesa.PENDENTE and 
                   hoje < d.vencimento <= tres_dias]
        
        return self.despesas.copy()
    
    def formatar_moeda(self, valor: float) -> str:
        """Formata valor como moeda brasileira"""
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    def dias_para_vencimento(self, despesa: Despesa) -> int:
        """Calcula dias para vencimento"""
        hoje = datetime.now().date()
        vencimento = despesa.vencimento.date()
        return (vencimento - hoje).days
    
    def get_despesa_por_id(self, id_despesa: int) -> Optional[Despesa]:
        """Obtém despesa por ID"""
        for despesa in self.despesas:
            if despesa.id == id_despesa:
                return despesa
        return None