/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { BurgerMenuDialog } from "@point_of_sale/app/components/navbar/burger_menu/burger_menu_dialog";
import { BridalPackageDialog } from "@alahram_retail_demo/app/bridal_package/bridal_package_dialog";

function launchBridalPackageDialog(componentInstance) {
    try {
        const dialogService =
            componentInstance.dialog ||
            componentInstance.env?.services?.dialog ||
            componentInstance.pos?.dialog;

        if (dialogService) {
            dialogService.add(BridalPackageDialog, {});
        } else {
            console.error("Dialog service not found on component:", componentInstance);
        }
    } catch (err) {
        console.error("Error launching BridalPackageDialog:", err);
    }
}

patch(Navbar.prototype, {
    onClickBridalPackage() {
        launchBridalPackageDialog(this);
    },
});

patch(BurgerMenuDialog.prototype, {
    openBridalPackage() {
        launchBridalPackageDialog(this);
    },
});
