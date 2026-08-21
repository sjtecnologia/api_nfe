"""
test_nfe_critical_regression.py

SUÍTE CRÍTICA DE REGRESSÃO PARA EMISSÃO NF-e

Testes simplificados que não dependem de fixtures complexas de DB.
Focam em verificações de código e rotas que podem ser testadas sem dados.
"""

import json
import os
import sys

import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ================================================================================
# TESTES CRÍTICOS SIMPLIFICADOS
# ================================================================================

class TestBlueprintCorreto:
    """Teste 1: Blueprint correto registrado em app.py"""
    
    def test_app_uses_routes_nfe_blueprint(self, app):
        """App utiliza routes.nfe_routes.nfe_bp, não nfe_routes.py da raiz"""
        
        # Verificar que blueprint 'nfe' está registrado
        assert 'nfe' in app.blueprints, \
            "Blueprint 'nfe' não registrado em app.blueprints"
        
        blueprint = app.blueprints['nfe']
        assert blueprint.import_name == 'routes.nfe_routes', \
            f"Blueprint nfe importado de módulo incorreto: {blueprint.import_name}"

        route_endpoints = {
            rule.endpoint: str(rule)
            for rule in app.url_map.iter_rules()
        }
        assert route_endpoints.get('nfe.emitir_nfe') == '/admin/nfe/emitir'
        assert route_endpoints.get('nfe.create') == '/admin/nfe/create'


class TestRotasExistem:
    """Teste 2: Rotas principais existem"""
    
    def test_nfe_routes_exist(self, app):
        """Verificar que rotas /emitir e /create existem"""
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        
        # Verificar que /admin/nfe/emitir existe
        emitir_routes = [r for r in rules if '/admin/nfe/emitir' in r]
        assert len(emitir_routes) > 0, \
            "/admin/nfe/emitir não encontrada nas rotas registradas"
        
        # Verificar que /admin/nfe/create existe  
        create_routes = [r for r in rules if '/admin/nfe/create' in r]
        assert len(create_routes) > 0, \
            "/admin/nfe/create não encontrada nas rotas registradas"


class TestCSRFEndpoint:
    """Teste 3: Endpoint /api/csrf-token existe e funciona"""
    
    def test_csrf_token_requires_login(self, client):
        """Usuário anônimo não pode renovar o token."""
        response = client.get('/api/csrf-token')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


class TestEmitirPageLoads:
    """Teste 4: Página de emissão carrega sem erro"""
    
    def test_get_emitir_page_does_not_error(self, client):
        """GET /admin/nfe/emitir retorna 200 ou 302 (redirect login)"""
        response = client.get('/admin/nfe/emitir?cliente_id=1')
        
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


class TestActionFieldLogic:
    """Teste 5: Lógica de action=emitir está presente no HTML"""
    
    def test_action_field_creation_in_code(self, app):
        """
        Verificar que o código HTML/JS que cria action=emitir existe
        em um dos arquivos de template de emissão
        """
        # Procurar no arquivo emitir.html
        template_path = 'templates/admin/nfes/emitir.html'
        
        with open(template_path, 'r') as f:
            content = f.read()

        assert "a.value='emitir'" in content or 'a.value="emitir"' in content
        assert '/api/csrf-token' in content


class TestDirectNativeEmitFlag:
    """Teste 6: Flag directNativeEmit está no template"""
    
    def test_direct_native_emit_flag_exists(self, app):
        """Verificar que dataset.directNativeEmit está no template"""
        template_path = 'templates/admin/nfes/emitir.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
        assert 'directNativeEmit' in content


class TestCSRFTokenRenewal:
    """Teste 7: Verificar que CSRF renewal via fetch está no template"""
    
    def test_csrf_renewal_in_template(self, app):
        """Template deve fazer fetch para /api/csrf-token antes do submit"""
        template_path = 'templates/admin/nfes/emitir.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
        assert "fetch('/api/csrf-token'" in content
        assert '.then(function(d)' in content
        assert 't.value=d.csrf_token' in content


class TestNativeFormSubmit:
    """Teste 8: Template usa submit nativo, não AJAX"""
    
    def test_native_form_submit_in_template(self, app):
        """Template deve usar HTMLFormElement.prototype.submit, não jQuery.post"""
        template_path = 'templates/admin/nfes/emitir.html'
        
        with open(template_path, 'r') as f:
            content = f.read()

        assert 'HTMLFormElement.prototype.submit.call' in content


class TestDANFERoute:
    """Teste 9: Rota DANFE existe"""
    
    def test_danfe_route_registered(self, app):
        """Verificar que rota /danfe/<id>/pdf está registrada"""
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        danfe_routes = [r for r in rules if 'danfe' in r and 'pdf' in r]
        
        assert len(danfe_routes) > 0, \
            "Rota de DANFE PDF não encontrada"


class TestProximoNumeroRoute:
    """Teste 10: Rota próximo número existe"""
    
    def test_proximo_numero_route_registered(self, app):
        """Verificar que rota de próximo número está registrada"""
        rule = next(
            (rule for rule in app.url_map.iter_rules()
             if rule.endpoint == 'nfe.api_proximo_numero'),
            None,
        )
        assert rule is not None
        assert str(rule) == '/admin/nfe/api/proximo-numero'
        assert 'GET' in rule.methods


class TestPermissionDecorators:
    """Teste 11: Decorators de permissão existem em rotas críticas"""
    
    def test_permission_required_decorator_exists(self, app):
        """Verificar que auth.decorators.permission_required existe"""
        try:
            from auth.decorators import permission_required, editor_or_admin_required
            assert callable(permission_required)
            assert callable(editor_or_admin_required)
        except ImportError:
            pytest.fail("Decorators de permissão não encontrados em auth.decorators")


class TestMultipleNFERoutes:
    """Teste 12: Ambas as rotas /create e /emitir estão registradas"""
    
    def test_both_create_and_emitir_routes(self, app):
        """Verificar que ambas /create e /emitir existem como rotas"""
        rules = {str(rule) for rule in app.url_map.iter_rules()}
        
        create_found = any('create' in r and '/admin/nfe' in r for r in rules)
        emitir_found = any('emitir' in r and '/admin/nfe' in r for r in rules)
        
        assert create_found, "/admin/nfe/create não registrada"
        assert emitir_found, "/admin/nfe/emitir não registrada"


class TestNFEModuleActive:
    """Teste 13: Módulo ativo é routes.nfe_routes, não raiz"""
    
    def test_active_nfe_module(self, app):
        """
        Verificar que o blueprint foi importado de routes.nfe_routes
        e não de nfe_routes (raiz)
        """
        assert app.blueprints['nfe'].import_name == 'routes.nfe_routes'
        assert 'nfe_routes' not in {
            name for name in sys.modules
            if name == 'nfe_routes'
        }


class TestTemplateActive:
    """Teste 14: Template ativo é templates/admin/nfes/emitir.html"""
    
    def test_active_template(self, app):
        """Verificar que template ativo é o correto"""
        assert os.path.exists('templates/admin/nfes/emitir.html')
        assert os.path.exists('routes/emitir.html')
        with open('routes/emitir.html', 'r') as f:
            assert 'DEPRECATED' in f.read()


class TestIncidentoEspecifico:
    """Teste 15: Regressão específica de 20/08/2026"""
    
    def test_incident_regression_protection(self, app):
        """
        Verificar que a proteção contra o incidente existe:
        - action=emitir é criado no onclick
        - CSRF é renovado via /api/csrf-token
        - submit é nativo
        """
        
        template_path = 'templates/admin/nfes/emitir.html'
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                content = f.read()
            
            # Três verificações principais do incidente
            checks = [
                ("a.value='emitir'" in content or 'a.value="emitir"' in content, 
                 "action=emitir não é criado"),
                ('/api/csrf-token' in content, 
                 "CSRF renewal endpoint não está no fetch"),
                ('HTMLFormElement.prototype.submit.call' in content, 
                 "submit nativo não está sendo usado"),
            ]
            
            for check, msg in checks:
                assert check, f"Proteção contra incidente falha: {msg}"

