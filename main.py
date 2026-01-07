"""
TRIMONEY - Aplicativo Mobile
main.py - Configuração principal do Kivy
"""

import os
os.environ['KIVY_NO_CONSOLELOG'] = '1'

from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ObjectProperty
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex
from kivy.app import App

from datetime import datetime
from financeiro import GerenciadorFinanceiro, CategoriaDespesa, StatusDespesa

# Carregar arquivo KV
Builder.load_file('trimoney.kv')

class TelaBase(Screen):
    """Classe base para todas as telas"""
    gerenciador = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gerenciador = App.get_running_app().gerenciador
        
    def mostrar_mensagem(self, titulo: str, mensagem: str, tipo: str = "info"):
        """Mostra mensagem na tela"""
        app = App.get_running_app()
        app.mostrar_dialogo(titulo, mensagem, tipo)

class TelaResumo(TelaBase):
    """Tela de resumo financeiro"""
    
    def on_pre_enter(self):
        """Atualiza dados ao entrar na tela"""
        self.atualizar_resumo()
    
    def atualizar_resumo(self):
        """Atualiza os dados do resumo"""
        if not self.gerenciador:
            return
            
        resumo = self.gerenciador.calcular_resumo()
        
        # Atualizar labels
        self.ids.saldo_atual.text = self.gerenciador.formatar_moeda(resumo['saldo_atual'])
        self.ids.total_gasto.text = self.gerenciador.formatar_moeda(resumo['total_gasto'])
        self.ids.total_pendente.text = self.gerenciador.formatar_moeda(resumo['total_pendente'])
        self.ids.saldo_final.text = self.gerenciador.formatar_moeda(resumo['saldo_final'])
        
        # Atualizar cor do saldo final
        if resumo['saldo_final'] >= 0:
            self.ids.card_saldo_final.md_bg_color = get_color_from_hex("#4CAF50")
        else:
            self.ids.card_saldo_final.md_bg_color = get_color_from_hex("#FF5252")
        
        # Mostrar alertas se houver
        if resumo['num_vencidas'] > 0 or resumo['num_proximas'] > 0:
            alertas = []
            if resumo['num_vencidas'] > 0:
                alertas.append(f"⚠️ {resumo['num_vencidas']} vencida(s)")
            if resumo['num_proximas'] > 0:
                alertas.append(f"⏰ {resumo['num_proximas']} próxima(s)")
            
            self.ids.lbl_alertas.text = " | ".join(alertas)
            self.ids.lbl_alertas.opacity = 1
        else:
            self.ids.lbl_alertas.opacity = 0

class TelaDespesas(TelaBase):
    """Tela de lista de despesas"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.despesa_selecionada = None
    
    def on_pre_enter(self):
        """Atualiza lista ao entrar na tela"""
        self.atualizar_lista()
    
    def atualizar_lista(self):
        """Atualiza a lista de despesas"""
        filtro = self.ids.spinner_filtro.text.lower()
        despesas = self.gerenciador.filtrar_despesas(filtro)
        
        # Limpar lista atual
        self.ids.lista_despesas.data = []
        
        # Adicionar despesas
        for despesa in despesas:
            dias = self.gerenciador.dias_para_vencimento(despesa)
            
            # Cor baseada no status e vencimento
            if despesa.status == StatusDespesa.PAGA:
                cor_status = get_color_from_hex("#4CAF50")
                texto_status = "✓ Paga"
            elif dias < 0:
                cor_status = get_color_from_hex("#FF5252")
                texto_status = f"Vencida ({abs(dias)} dias)"
            elif dias <= 3:
                cor_status = get_color_from_hex("#FF9800")
                texto_status = f"Vence em {dias} dias"
            else:
                cor_status = get_color_from_hex("#2196F3")
                texto_status = f"Vence em {dias} dias"
            
            self.ids.lista_despesas.data.append({
                'id': despesa.id,
                'nome': despesa.nome,
                'valor': self.gerenciador.formatar_moeda(despesa.valor),
                'vencimento': despesa.vencimento.strftime("%d/%m/%Y"),
                'categoria': despesa.categoria.value,
                'status': texto_status,
                'cor_status': cor_status,
                'selecionada': False
            })
    
    def on_despesa_selecionada(self, id_despesa):
        """Quando uma despesa é selecionada"""
        self.despesa_selecionada = id_despesa
        self.ids.btn_pagar.disabled = False
        self.ids.btn_excluir.disabled = False
        
        # Verificar se pode pagar
        despesa = self.gerenciador.get_despesa_por_id(id_despesa)
        if despesa and despesa.status == StatusDespesa.PAGA:
            self.ids.btn_pagar.disabled = True
    
    def pagar_despesa(self):
        """Marca despesa como paga"""
        if not self.despesa_selecionada:
            self.mostrar_mensagem("Aviso", "Selecione uma despesa primeiro!")
            return
        
        try:
            sucesso = self.gerenciador.marcar_despesa_como_paga(self.despesa_selecionada)
            if sucesso:
                self.mostrar_mensagem("Sucesso", "Despesa marcada como paga!")
                self.atualizar_lista()
                self.limpar_selecao()
            else:
                self.mostrar_mensagem("Erro", "Não foi possível pagar a despesa!")
        except ValueError as e:
            self.mostrar_mensagem("Erro", str(e))
    
    def excluir_despesa(self):
        """Exclui despesa selecionada"""
        if not self.despesa_selecionada:
            self.mostrar_mensagem("Aviso", "Selecione uma despesa primeiro!")
            return
        
        # TODO: Adicionar confirmação
        self.gerenciador.excluir_despesa(self.despesa_selecionada)
        self.mostrar_mensagem("Sucesso", "Despesa excluída!")
        self.atualizar_lista()
        self.limpar_selecao()
    
    def limpar_selecao(self):
        """Limpa a seleção atual"""
        self.despesa_selecionada = None
        self.ids.btn_pagar.disabled = True
        self.ids.btn_excluir.disabled = True

class TelaNovaDespesa(TelaBase):
    """Tela para adicionar nova despesa"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self._configurar_data, 0.5)
    
    def _configurar_data(self, dt):
        """Configura data padrão"""
        hoje = datetime.now()
        self.ids.data_input.text = hoje.strftime("%d/%m/%Y")
    
    def adicionar_despesa(self):
        """Adiciona nova despesa"""
        # Obter valores
        nome = self.ids.nome_input.text.strip()
        valor_texto = self.ids.valor_input.text.strip()
        data_texto = self.ids.data_input.text.strip()
        categoria = self.ids.categoria_spinner.text
        
        # Validar
        if not nome:
            self.mostrar_mensagem("Erro", "Digite o nome da despesa!")
            return
        
        if not valor_texto:
            self.mostrar_mensagem("Erro", "Digite o valor da despesa!")
            return
        
        if not data_texto:
            self.mostrar_mensagem("Erro", "Digite a data de vencimento!")
            return
        
        try:
            # Converter valor
            valor = float(valor_texto.replace(",", "."))
            
            # Converter data
            try:
                data = datetime.strptime(data_texto, "%d/%m/%Y")
            except:
                self.mostrar_mensagem("Erro", "Data inválida! Use DD/MM/AAAA")
                return
            
            # Converter categoria
            if categoria == "Fixa":
                categoria_enum = CategoriaDespesa.FIXA
            else:
                categoria_enum = CategoriaDespesa.VARIAVEL
            
            # Adicionar despesa
            self.gerenciador.adicionar_despesa(nome, valor, data, categoria_enum)
            
            # Limpar campos
            self.ids.nome_input.text = ""
            self.ids.valor_input.text = ""
            hoje = datetime.now()
            self.ids.data_input.text = hoje.strftime("%d/%m/%Y")
            
            self.mostrar_mensagem("Sucesso", "Despesa adicionada com sucesso!")
            
            # Voltar para tela de despesas
            self.manager.current = 'despesas'
            
        except ValueError as e:
            self.mostrar_mensagem("Erro", f"Valor inválido!\n{str(e)}")

class TelaSaldo(TelaBase):
    """Tela para gerenciar saldo"""
    
    def atualizar_saldo(self):
        """Atualiza o saldo com valor digitado"""
        valor_texto = self.ids.saldo_input.text.strip()
        
        if not valor_texto:
            self.mostrar_mensagem("Aviso", "Digite um valor!")
            return
        
        try:
            valor = float(valor_texto.replace(",", "."))
            self.gerenciador.definir_saldo(valor)
            self.mostrar_mensagem("Sucesso", "Saldo atualizado com sucesso!")
            self.ids.saldo_input.text = ""
            
            # Atualizar tela de resumo
            tela_resumo = self.manager.get_screen('resumo')
            tela_resumo.atualizar_resumo()
            
        except ValueError:
            self.mostrar_mensagem("Erro", "Digite um valor válido!")
    
    def adicionar_saldo(self):
        """Adiciona valor ao saldo atual"""
        valor_texto = self.ids.saldo_input.text.strip()
        
        if not valor_texto:
            self.mostrar_mensagem("Aviso", "Digite um valor!")
            return
        
        try:
            valor = float(valor_texto.replace(",", "."))
            self.gerenciador.adicionar_saldo(valor)
            self.mostrar_mensagem("Sucesso", f"R$ {valor:.2f} adicionados ao saldo!")
            self.ids.saldo_input.text = ""
            
            # Atualizar tela de resumo
            tela_resumo = self.manager.get_screen('resumo')
            tela_resumo.atualizar_resumo()
            
        except ValueError:
            self.mostrar_mensagem("Erro", "Digite um valor válido!")

class GerenciadorTelas(ScreenManager):
    """Gerenciador de telas do aplicativo"""
    pass

class ItemDespesa(BoxLayout):
    """Item individual da lista de despesas"""
    id_despesa = NumericProperty(0)
    nome = StringProperty("")
    valor = StringProperty("")
    vencimento = StringProperty("")
    categoria = StringProperty("")
    status = StringProperty("")
    cor_status = ObjectProperty(get_color_from_hex("#2196F3"))
    selecionada = BooleanProperty(False)

class ListaDespesas(RecycleView):
    """Lista de despesas com seleção"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []

class TrimoneyApp(App):
    """Aplicativo principal"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gerenciador = None
        self.dialogo = None
    
    def build(self):
        """Constrói a interface do aplicativo"""
        self.title = "TRIMONEY"
        
        # Inicializar gerenciador financeiro
        self.gerenciador = GerenciadorFinanceiro()
        
        # Configurar cores da janela
        Window.clearcolor = get_color_from_hex("#1A1A2E")
        
        # Criar gerenciador de telas
        sm = GerenciadorTelas()
        sm.transition = SlideTransition()
        
        # Adicionar telas
        sm.add_widget(TelaResumo(name='resumo'))
        sm.add_widget(TelaDespesas(name='despesas'))
        sm.add_widget(TelaNovaDespesa(name='nova_despesa'))
        sm.add_widget(TelaSaldo(name='saldo'))
        
        return sm
    
    def mostrar_dialogo(self, titulo: str, mensagem: str, tipo: str = "info"):
        """Mostra diálogo de mensagem"""
        from kivy.uix.popup import Popup
        from kivy.uix.label import Label
        from kivy.uix.boxlayout import BoxLayout
        
        # Criar conteúdo
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(text=mensagem, halign='center', valign='middle'))
        
        # Botão OK
        btn_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        btn_ok = Button(text="OK", size_hint_x=1)
        btn_layout.add_widget(btn_ok)
        content.add_widget(btn_layout)
        
        # Criar popup
        popup = Popup(
            title=titulo,
            content=content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False
        )
        
        # Configurar cor baseada no tipo
        if tipo == "erro":
            popup.title_color = get_color_from_hex("#FF5252")
        elif tipo == "sucesso":
            popup.title_color = get_color_from_hex("#4CAF50")
        else:
            popup.title_color = get_color_from_hex("#2196F3")
        
        # Botão fechar
        btn_ok.bind(on_release=popup.dismiss)
        
        popup.open()
    
    def on_pause(self):
        """Chamado quando o app vai para segundo plano"""
        if self.gerenciador:
            self.gerenciador.salvar_dados()
        return True
    
    def on_resume(self):
        """Chamado quando o app volta ao primeiro plano"""
        if self.gerenciador:
            self.gerenciador.carregar_dados()
        return True
    
    def on_stop(self):
        """Chamado quando o app é fechado"""
        if self.gerenciador:
            self.gerenciador.salvar_dados()

if __name__ == '__main__':
    TrimoneyApp().run()