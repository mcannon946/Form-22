// Canonical AcroForm field map for NC Form 22
export const FIELD_MAP = [
    // Employee
  { id: 'employee_name',       label: 'Employee Name',          type: 'text',     section: 'employee', maxLength: 60 },
  { id: 'employee_address',    label: 'Employee Address',       type: 'text',     section: 'employee', maxLength: 80 },
  { id: 'employee_city',       label: 'City',                   type: 'text',     section: 'employee', maxLength: 40 },
  { id: 'employee_state',      label: 'State',                  type: 'text',     section: 'employee', maxLength: 2  },
  { id: 'employee_zip',        label: 'Zip',                    type: 'text',     section: 'employee', maxLength: 10 },
  { id: 'employee_ssn',        label: 'SSN',                    type: 'text',     section: 'employee', maxLength: 11 },
  { id: 'employee_dob',        label: 'Date of Birth',          type: 'date',     section: 'employee' },
  { id: 'employee_gender',     label: 'Gender',                 type: 'text',     section: 'employee', maxLength: 1  },
    // Employer
  { id: 'employer_name',       label: 'Employer Name',          type: 'text',     section: 'employer', maxLength: 60 },
  { id: 'employer_address',    label: 'Employer Address',       type: 'text',     section: 'employer', maxLength: 80 },
  { id: 'employer_phone',      label: 'Employer Phone',         type: 'text',     section: 'employer', maxLength: 15 },
  { id: 'employer_fein',       label: 'FEIN',                   type: 'text',     section: 'employer', maxLength: 10 },
    // Injury
  { id: 'doi',                 label: 'Date of Injury',         type: 'date',     section: 'injury'   },
  { id: 'injury_description',  label: 'Injury Description',     type: 'text',     section: 'injury',  maxLength: 200 },
  { id: 'injury_body_part',    label: 'Body Part',              type: 'text',     section: 'injury',  maxLength: 60  },
  { id: 'return_to_work_date', label: 'Return to Work Date',   type: 'date',     section: 'injury'   },
    // Wages
  { id: 'aww',                 label: 'Average Weekly Wage',   type: 'currency', section: 'wages'    },
  { id: 'comp_rate',           label: 'Compensation Rate',     type: 'currency', section: 'wages'    },
  { id: 'wage_period_start',   label: 'Wage Period Start',     type: 'date',     section: 'wages'    },
  { id: 'wage_period_end',     label: 'Wage Period End',       type: 'date',     section: 'wages'    },
    // Weekly wage rows (52 weeks)
    ...Array.from({ length: 52 }, (_, i) => ({ id: `week_${i+1}_wages`, label: `Week ${i+1} Wages`, type: 'currency', section: 'wages' })),
    // Benefits
  { id: 'ttd_start',           label: 'TTD Start Date',        type: 'date',     section: 'benefits' },
  { id: 'ttd_end',             label: 'TTD End Date',          type: 'date',     section: 'benefits' },
  { id: 'ttd_weeks',           label: 'TTD Weeks Paid',        type: 'number',   section: 'benefits' },
  { id: 'mmi_date',            label: 'MMI Date',              type: 'date',     section: 'benefits' },
  { id: 'ratings',             label: 'Permanent Impairment %', type: 'number', section: 'benefits' },
    // Signatures
  { id: 'preparer_name',       label: 'Preparer Name',         type: 'text',     section: 'signatures', maxLength: 60 },
  { id: 'preparer_title',      label: 'Preparer Title',        type: 'text',     section: 'signatures', maxLength: 60 },
  { id: 'preparer_date',       label: 'Preparation Date',      type: 'date',     section: 'signatures' },
  { id: 'preparer_phone',      label: 'Preparer Phone',        type: 'text',     section: 'signatures', maxLength: 15 },
  ];

export const FIELD_INDEX = Object.fromEntries(FIELD_MAP.map(f => [f.id, f]));
export default FIELD_MAP;
