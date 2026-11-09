/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { BurgerMenuDialog } from "@point_of_sale/app/components/navbar/burger_menu/burger_menu_dialog";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { BranchReservationDialog } from "@alahram_retail_demo/app/branch_reservation/branch_reservation_dialog";

function launchBranchReservationDialog(componentInstance) {
    try {
        const dialogService =
            componentInstance.dialog ||
            componentInstance.env?.services?.dialog ||
            componentInstance.pos?.dialog;

        if (dialogService) {
            dialogService.add(BranchReservationDialog, {});
        } else {
            console.error("Dialog service not found on component:", componentInstance);
        }
    } catch (err) {
        console.error("Error launching BranchReservationDialog:", err);
    }
}

patch(Navbar.prototype, {
    onClickBranchReservation() {
        launchBranchReservationDialog(this);
    },
});

patch(BurgerMenuDialog.prototype, {
    openBranchReservation() {
        launchBranchReservationDialog(this);
    },
});

patch(ActionpadWidget.prototype, {
    onClickBranchReservation() {
        launchBranchReservationDialog(this);
    },
});

patch(ControlButtons.prototype, {
    onClickBranchReservation() {
        launchBranchReservationDialog(this);
    },
});
