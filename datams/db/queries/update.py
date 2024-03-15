from typing import Any, Dict
from sqlalchemy import insert, update, delete
from datams.db.queries.select import (select_contacts, select_organizations,
                                      select_equipment, select_deployments)
from datams.db.core import query_all
from datams.db.tables import (Contact, Deployment, File, Mooring, Organization,
                              Equipment, DeploymentOrganization, DeploymentContact,
                              MooringEquipment, User)


def update_query(table, values, **kwargs):
    if table == 'Contact':
        update_contact(kwargs['contact_id'], values)
    elif table == 'Deployment':
        update_deployment(kwargs['deployment_id'], values)
    elif table == 'Equipment':
        update_equipment(kwargs['equipment_id'], values)
    elif table == 'File':
        update_files(kwargs['file_id'], values)
    elif table == 'Mooring':
        update_mooring(kwargs['mooring_id'], values)
    elif table == 'Organization':
        update_organization(kwargs['organization_id'], values)
    elif table == 'User':
        update_user(kwargs['user_id'], values)
    else:
        raise NotImplementedError


def update_contact(contact_id, values: Dict[str, Any]):
    query_all([update(Contact).values(**values).where(Contact.id == contact_id)])


def update_user(user_id, values: Dict[str, Any]):
    query_all([update(User).values(**values).where(User.id == user_id)])


def update_deployment(deployment_id, values: Dict[str, Any]):
    # updated contacts
    prev_contact_ids = list(
        select_contacts(view='deployment.edit', deployment_id=deployment_id)['id']
    )
    new_contact_ids = values.pop('contact_ids')
    contact_ids_to_remove = set(prev_contact_ids).difference(new_contact_ids)
    contact_ids_to_add = set(new_contact_ids).difference(prev_contact_ids)
    # remove deselected contacts
    query_all([delete(DeploymentContact)
              .where(DeploymentContact.contact_id.in_(contact_ids_to_remove))
              .where(DeploymentContact.deployment_id == deployment_id)])
    # add newly selected contacts
    query_all([insert(DeploymentContact)
              .values(deployment_id=deployment_id, contact_id=contact_id)
               for contact_id in contact_ids_to_add])

    # # remove all existing
    # query_all([delete(DeploymentContact)
    #           .where(DeploymentContact.deployment_id == deployment_id)])
    # # add all selected
    # query_all([insert(DeploymentContact)
    #           .values(deployment_id=deployment_id, contact_id=contact_id)
    #            for contact_id in new_contact_ids])

    prev_organization_ids = list(
        select_organizations(view='deployment.edit', deployment_id=deployment_id)['id']
    )
    new_organization_ids = values.pop('organization_ids')
    organization_ids_to_remove = set(prev_organization_ids).difference(new_organization_ids)
    organization_ids_to_add = set(new_organization_ids).difference(prev_organization_ids)
    # remove deselected organizations
    query_all([delete(DeploymentOrganization)
              .where(DeploymentOrganization.organization_id.in_(organization_ids_to_remove))
              .where(DeploymentOrganization.deployment_id == deployment_id)])
    # add newly selected organizations
    query_all([insert(DeploymentOrganization)
              .values(deployment_id=deployment_id, organization_id=organization_id)
               for organization_id in organization_ids_to_add])

    # # remove existing
    # query_all([delete(DeploymentOrganization)
    #           .where(DeploymentOrganization.deployment_id == deployment_id)])
    # # add new
    # query_all([
    #     insert(DeploymentOrganization)
    #     .values(deployment_id=deployment_id, organization_id=organization_id)
    #     for organization_id in organization_ids
    # ])

    # update the deployment information
    query_all(
        [update(Deployment).values(**values).where(Deployment.id == deployment_id)])


def update_files(values):
    indexes = values.pop('indexes')
    query_all([update(File).values(**values).where(File.id.in_(indexes))])


def update_equipment(equipment_id, values: Dict[str, Any]):
    query_all([update(Equipment).values(**values).where(Equipment.id == equipment_id)])


def update_mooring(mooring_id, values: Dict[str, Any]):
    prev_equipment_ids = list(
        select_equipment(view='mooring.edit', mooring_id=mooring_id)['id']
    )
    new_equipment_ids = values.pop('equipment_ids')
    equipment_ids_to_remove = set(prev_equipment_ids).difference(new_equipment_ids)
    equipment_ids_to_add = set(new_equipment_ids).difference(prev_equipment_ids)
    # remove deselected equipment
    query_all([delete(MooringEquipment)
              .where(MooringEquipment.equipment_id.in_(equipment_ids_to_remove))
              .where(MooringEquipment.mooring_id == mooring_id)])
    # add newly selected equipment
    query_all([insert(MooringEquipment)
              .values(mooring_id=mooring_id, equipment_id=equipment_id)
               for equipment_id in equipment_ids_to_add])

    # # remove existing
    # query_all([delete(MooringEquipment)
    #           .where(MooringEquipment.mooring_id == mooring_id)])
    # # add new
    # query_all([insert(MooringEquipment)
    #           .values(mooring_id=mooring_id, equipment_id=equipment_id)
    #            for equipment_id in equipment_ids])

    query_all([update(Mooring).values(**values).where(Mooring.id == mooring_id)])


def update_organization(organization_id, values: Dict[str, Any]):
    # update associated contacts
    prev_contact_ids = list(
        select_contacts(view='organization.edit', organization_id=organization_id)['id']
    )
    new_contact_ids = values.pop('contact_ids')
    contact_ids_to_remove = set(prev_contact_ids).difference(new_contact_ids)
    contact_ids_to_add = set(new_contact_ids).difference(prev_contact_ids)

    # remove deselected
    query_all([update(Contact).values(organization_id=None)
              .where(Contact.id.in_(contact_ids_to_remove))])
    # add newly selected
    query_all([update(Contact).values(organization_id=organization_id)
              .where(Contact.id.in_(contact_ids_to_add))])

    # # remove existing
    # query_all([update(Contact).values(organization_id=None)
    #           .where(Contact.organization_id == organization_id)])
    # # add new
    # query_all([update(Contact).values(organization_id=organization_id)
    #           .where(Contact.id.in_(contact_ids))])

    # updated associated deployments
    prev_deployment_ids = list(
        select_deployments(view='organization.edit', organization_id=organization_id)['id']
    )
    new_deployment_ids = values.pop('deployment_ids')
    deployment_ids_to_remove = set(prev_deployment_ids).difference(new_deployment_ids)
    deployment_ids_to_add = set(new_deployment_ids).difference(prev_deployment_ids)

    # remove deselected deployments
    query_all([delete(DeploymentOrganization)
              .where(DeploymentOrganization.deployment_id.in_(deployment_ids_to_remove))
              .where(DeploymentOrganization.organization_id == organization_id)])
    # add newly selected deployments
    query_all([insert(DeploymentOrganization)
              .values(deployment_id=deployment_id, organization_id=organization_id)
               for deployment_id in deployment_ids_to_add])

    # # remove existing
    # query_all([delete(DeploymentOrganization)
    #           .where(DeploymentOrganization.organization_id == organization_id)])
    # # add new
    # query_all([insert(DeploymentOrganization)
    #            .values(deployment_id=deployment_id, organization_id=organization_id)
    #            for deployment_id in deployment_ids])

    prev_equipment_ids = list(
        select_equipment(view='organization.edit', organization_id=organization_id)['id']
    )
    new_equipment_ids = values.pop('equipment_ids')

    equipment_ids_to_remove = set(prev_equipment_ids).difference(new_equipment_ids)
    equipment_ids_to_add = set(new_equipment_ids).difference(prev_equipment_ids)

    # remove deselected equipment
    query_all([update(Equipment).values(organization_id=None)
              .where(Equipment.id.in_(equipment_ids_to_remove))])
    # add newly selected equipment
    query_all([update(Equipment).values(organization_id=organization_id)
              .where(Equipment.id.in_(equipment_ids_to_add))])
    # # remove existing
    # query_all([update(Equipment).values(organization_id=None)
    #           .where(Equipment.organization_id == organization_id)])
    # # add new
    # query_all([update(Equipment).values(organization_id=organization_id)
    #           .where(Equipment.id.in_(equipment_ids))])

    # update organization
    query_all([update(Organization)
              .values(**values)
              .where(Organization.id == organization_id)])
