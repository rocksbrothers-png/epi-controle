from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _index_html() -> str:
    return (_repo_root() / "static" / "index.html").read_text(encoding="utf-8")


def _app_js() -> str:
    return (_repo_root() / "static" / "app.js").read_text(encoding="utf-8")


def test_login_username_field_has_inline_icon_without_changing_autocomplete():
    html = _index_html()

    assert 'class="login-input-field"' in html
    assert 'class="login-input-icon" aria-hidden="true"' in html
    assert 'id="login-username" name="username" type="text" autocomplete="username"' in html
    assert 'placeholder="Informe seu usuário"' in html


def test_login_password_field_keeps_autocomplete_and_has_toggle_button():
    html = _index_html()

    assert 'class="login-input-field login-input-field--password"' in html
    assert 'id="login-password" name="password" type="password" autocomplete="current-password"' in html
    assert 'id="login-password-toggle"' in html
    assert 'type="button"' in html
    assert 'aria-controls="login-password"' in html
    assert 'aria-pressed="false"' in html
    assert 'login-password-eye--open' in html
    assert 'login-password-eye--closed' in html


def test_login_password_toggle_is_single_scoped_binding():
    source = _app_js()

    assert source.count("loginPasswordToggle: document.getElementById('login-password-toggle')") == 1
    assert source.count("function setLoginPasswordVisibility") == 1
    assert source.count("function toggleLoginPasswordVisibility") == 1
    assert source.count("bindAppListener(refs.loginPasswordToggle, 'click', toggleLoginPasswordVisibility)") == 1
    assert "refs.loginPassword.type = isVisible ? 'text' : 'password';" in source
    assert "aria-label', isVisible ? 'Ocultar senha' : 'Mostrar senha'" in source
