"""
Pacote admin — cog de comandos administrativos do HugMe Bot.

Estrutura:
  utils.py              — check_is_owner, _build_role_config_embed
  views_base.py         — ConfirmView, ConfirmationView
  modals_pix.py         — SetQRCodeModal, ConfigureRoleModal, ConfirmationModal
  views_pix.py          — PIXConfigView
  views_roles.py        — PaginatedRoleSelectView, DefaultRoleSelectView,
                          TimeRoleModal, TimeUnitSelectView, TimeRoleSelectView,
                          TimeRoleConfigView, RoleConfigView
  views_supporter.py    — SupporterActionModal, SupporterPauseModal,
                          SupporterResumeModal, SupporterRemoveModal,
                          SupporterTimeTypeSelectView, SupporterUnitSelectView,
                          ManageSupporterActionView, ManageSupporterView
  views_dashboard.py    — SupportersPaginationView, DashboardView
  cog.py                — AdminCommands + setup()
"""

from .cog import setup
