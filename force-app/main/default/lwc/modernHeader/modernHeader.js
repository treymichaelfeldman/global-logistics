import { LightningElement } from 'lwc';
import GLOBAL_LOGISTICS_MODERN from '@salesforce/resourceUrl/GlobalLogisticsModern';

export default class ModernHeader extends LightningElement {
    logoUrl = `${GLOBAL_LOGISTICS_MODERN}/logo.svg`;

    handleLogin() {
        console.log('Login clicked');
    }
}