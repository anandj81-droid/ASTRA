# Astra Platform — Polish Backlog

## Deprecation warnings (safe to defer until Phase 4 done)
- [ ] core/database.py:34 — replace declarative_base() with sqlalchemy.orm.declarative_base()
- [ ] core/main.py:331,357 — migrate @app.on_event to lifespan= handlers
- [ ] All models — replace datetime.utcnow() with datetime.now(datetime.UTC)

## Module base contract refactor (before Module 5)
- [ ] Move register_routes(app) call into ModuleRegistry.initialize_all()
      so modules don't each need to call it themselves
- [ ] Remove self.register_routes(app) from fx_tool/cost_optimizer/last_mile initialize()
- [ ] Verify no duplicate route registration

## Cosmetic
- [ ] Add get_api_prefix() to any module missing it (defensive)
